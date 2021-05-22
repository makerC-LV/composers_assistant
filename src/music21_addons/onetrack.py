import fractions
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Union, Tuple, Any

from lark import Lark, Transformer, Token, ParseError
from music21 import volume, stream, duration, chord, midi, note

import logging

logger = logging.getLogger(__name__)

DEFAULT_VOLUME = 60
DEFAULT_DURATION = 'q'
DEFAULT_OCTAVE = 4
QL_MAP = {'w': 4, 'h': 2, 'q': 1, 't': 0.5, 's': 0.25}
REVERSE_QL_MAP = {v: k for k, v in QL_MAP.items()}


@dataclass
class Located():
    def __init__(self, start_line: int = 0,
                 start_column: int = 0,
                 end_line: int = 0,
                 end_column: int = 0):
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column

    def location(self):
        return (self.start_line, self.start_column, self.end_line, self.end_column)

    def _loc(self):
        return f'{self.start_line}:{self.start_column}-{self.end_line}:{self.end_column}'

    def location_intersects(self, sl, sc, el, ec):
        (ssl, ssc, sel, sec) = self.location()
        if el < ssl or (el == ssl and ec < ssc):  # other interval ends before this starts
            return False
        elif sl > sel or (sl == sel and sc > sec):  # other interval starts after this ends
            return False
        return True


def get_location(*args):
    args = [x for x in args if x is not None]
    if len(args) == 1:
        if isinstance(args[0], str):
            return args[0].line, args[0].column, args[0].end_line, args[0].end_column
        elif isinstance(args[0], list):
            return get_location(*args[0])
        else:
            raise ValueError('Unknown arg type:', type(args[0]))
    else:
        ssl, ssc, sel, sec = get_location(args[0])
        esl, esc, eel, eec = get_location(args[-1])
        return ssl, ssc, eel, eec


def onetrack_parser():
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))
    grammar_file = os.path.join(__location__, 'onetrack.grammar')
    with open(grammar_file, 'r') as gf:
        grammar = gf.read()
    # print(grammar)

    parser = Lark(grammar, start='part')
    return parser


class PNote(Located):
    def __init__(self, ppitch: Token, duration: Optional[Token] = None, velocity: Optional[Token] = None):
        super().__init__()
        self.pitch = ppitch
        self.duration = duration
        self.velocity = velocity
        self.start_line, self.start_column, self.end_line, self.end_column = \
            get_location(self.pitch, self.duration, self.velocity)

    def __repr__(self):
        return f'PNote:{self.pitch}{self.duration}{self.velocity}[{self._loc()}]'

    def __str__(self):
        s = str(self.pitch)
        if self.duration:
            s += self.duration
        if self.velocity:
            s += ':' + self.velocity
        return s


class PChord(Located):
    def __init__(self, pitches: List[Token], duration: Optional[Token] = None, velocity: Optional[Token] = None):
        super().__init__()
        self.pitches = pitches
        self.duration = duration
        self.velocity = velocity
        self.start_line, self.start_column, self.end_line, self.end_column = \
            get_location(self.pitches, self.duration, self.velocity)

    def __repr__(self):
        pl = [str(x) for x in self.pitches]
        return f'PChord:{pl}{self.duration}{self.velocity}[{self._loc()}]'

    def __str__(self):
        s = '[' + ' '.join([str(p) for p in self.pitches]) + ']'
        if self.duration:
            s += self.duration
        if self.velocity:
            s += ':' + self.velocity
        return s


class SetVol(Located):
    def __init__(self, velocity: int):
        self.velocity = velocity
        self.start_line, self.start_column, self.end_line, self.end_column = \
            get_location(self.velocity)

    def __repr__(self):
        return f'V{self.velocity}[{self._loc()}]'

    def __str__(self):
        return 'v:' + str(self.velocity)


def get_ql(dur):
    if dur is None:
        dur = DEFAULT_DURATION
    length = dur[0]
    base = QL_MAP.get(length)
    if len(dur) > 1:
        base *= 1.5
    return base


def get_velocity(vol, default=DEFAULT_VOLUME):
    if vol is None:
        return default
    else:
        return int(vol)


class OneTrackTransformer(Transformer):
    def __init__(self, debug=False):
        super().__init__()
        self.vol = DEFAULT_VOLUME
        self.pdebug = debug

    def debug(self, *args, **kwargs):
        if self.pdebug:
            print(*args, **kwargs)

    def duration(self, dur):
        self.debug("duration:", dur, "ret:", dur[0])
        return ('duration', dur[0])

    def volume(self, vol):
        self.debug("volume:", vol, "ret", vol[0])
        return ('volume', vol[0])

    def pitch(self, p):
        self.debug("pitch:", p, "ret:", p[0])
        return ('pitch', p[0])

    def note(self, p):
        pitch, duration, velocity = None, None, None
        for type, token in p:
            if type == 'pitch':
                pitch = token
            if type == 'duration':
                duration = token
            if type == 'volume':
                velocity = token
        rv = PNote(pitch, duration, velocity)
        self.debug("Note:", p, "ret:", rv)
        return rv

    def chord_desc(self, cd):
        self.debug("chord_desc", cd, "ret", cd)
        return ('chord_desc', [x[1] for x in cd])

    def chord(self, c):
        pitches, duration, velocity = None, None, None
        for type, token in c:
            if type == 'chord_desc':
                pitches = token
            if type == 'duration':
                duration = token
            if type == 'volume':
                velocity = token
        rv = PChord(pitches, duration, velocity)
        self.debug("chord", c, "ret", rv)
        return rv

    def setvol(self, vol):
        self.debug("setvol:", vol, "ret", vol[0])
        type, token = vol[0]
        sv = SetVol(token)
        return sv

    def item(self, i):
        self.debug('item:', i, "ret", i[0])
        return i[0]

    def part(self, items):
        self.debug("part:", items)
        return items


def to_text(obj_list) -> str:
    return ' '.join([str(x) for x in obj_list])


def to_part(obj_list, track=None) -> Tuple[stream.Part, Dict[int, Tuple[Union[PChord, PNote], note.GeneralNote, Any]]]:
    map = {}  # type: Dict[int, Tuple[Union[PChord, PNote], note.GeneralNote, Any]]
    curr_vel = DEFAULT_VOLUME
    part = stream.Part()
    for cn in obj_list:
        if isinstance(cn, PNote):
            if cn.pitch.lower() == "r":
                n = note.Rest()
            else:
                n = note.Note(cn.pitch)
                if n.pitch.octave is None:
                    n.pitch.octave = DEFAULT_OCTAVE
            ql = get_ql(cn.duration)
            n.duration = duration.Duration(fractions.Fraction(ql))
            if n.isNote:
                vel = get_velocity(cn.velocity, default=curr_vel)
                n.volume = volume.Volume(velocity=vel)
            part.append(n)
            map[id(n)] = (cn, n, track)
        elif isinstance(cn, PChord):
            ch = chord.Chord(cn.pitches)
            for p in ch.pitches:
                if p.octave is None:
                    p.octave = DEFAULT_OCTAVE
            ql = get_ql(cn.duration)
            ch.duration = duration.Duration(fractions.Fraction(ql))
            vel = get_velocity(cn.velocity, default=curr_vel)
            ch.volume = volume.Volume(velocity=vel)
            part.append(ch)
            map[id(ch)] = (cn, ch, track)
        elif isinstance(cn, SetVol):
            curr_vel = int(cn.velocity)
        else:
            raise ParseError("Unknown object", cn.__class__)
    return part, map


def parse_onetrack(text) -> List:
    parser = onetrack_parser()
    tree = parser.parse(text)
    nl = OneTrackTransformer().transform(tree)  # type: List
    return nl


def onetrack_to_part(text, parser, id=None):
    tree = parser.parse(text)
    nl = OneTrackTransformer().transform(tree)
    return to_part(nl, id)


def get_duration_string(dur):
    if dur is None:
        return ''
    else:
        ql = dur.quarterLength
        if ql == 1:
            return ''
        else:
            return REVERSE_QL_MAP[ql]


def volume_to_string(volume, current_velocity):
    if volume is not None and volume.velocity != current_velocity:
        return ":" + str(volume.velocity), volume.velocity
    else:
        return '', current_velocity


def part_to_onetrack(part: stream.Part):
    part.makeRests()
    symbols = []  # type: List[str]
    current_velocity = 0
    for ncr in part.flat.getElementsByClass(['Note', 'Chord', 'Rest']):
        ds = get_duration_string(ncr.duration)
        if isinstance(ncr, note.Rest):
            symbols.append('r' + ds)
        elif isinstance(ncr, note.Note):
            vstr, current_velocity = volume_to_string(ncr.volume, current_velocity)
            if vstr:
                symbols.append('v' + vstr)
                symbols.append(' ')
            if ncr.pitch.octave == DEFAULT_OCTAVE:
                ncr.pitch.octave = None
            symbols.append(ncr.nameWithOctave)
            symbols.append(ds)
        elif isinstance(ncr, chord.Chord):
            vstr, current_velocity = volume_to_string(ncr.volume, current_velocity)
            if vstr:
                symbols.append('v' + vstr)
                symbols.append(' ')
            symbols.append('[')
            for p in ncr.pitches:
                if p.octave == DEFAULT_OCTAVE:
                    p.octave = None
                symbols.append(p.nameWithOctave)
                symbols.append(' ')
            symbols.append(']')
            symbols.append(ds)

        else:
            raise Exception("Unknown type:", ncr)

        symbols.append(' ')
    return ''.join(symbols)


def main():
    parser = onetrack_parser()
    tree = parser.parse("C-3 Aq A:100 Aq:100 [a b4]q [c d]q :100 v:60")
    print(tree.pretty())
    nl = OneTrackTransformer().transform(tree)
    print(to_text(nl))
    score = stream.Score()
    score.insert(0, to_part(nl)[0])
    sp = midi.realtime.StreamPlayer(score)
    sp.play()


if __name__ == "__main__":
    main()
