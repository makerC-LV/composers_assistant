from music21 import stream, instrument

from music21_addons.onetrack import parse_onetrack, to_part
from music21_addons.sequencer import MySequencer, MidoSynth


def now_playing_fn(pl=None):
    print("now playing:", pl)


def pupdate(pos, length):
    print("pupdate:", pos, length)


def test_one():
    s = "C-6 Aq A:100 Aq:100 [a b4]q [c d]q:100 v:60"
    p, map = to_part(parse_onetrack(s))
    p.insert(0, instrument.instrumentFromMidiProgram(0))
    score = stream.Score()
    score.insert(0, p)
    # print(map)
    # score.show('text')
    # TODO: use textsynth and check output
    seq = MySequencer(MidoSynth())
    seq.play(score, 120, now_playing=now_playing_fn, progress_update=pupdate)
