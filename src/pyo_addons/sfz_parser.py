import math
import os
import re
from io import open

from utils import elogger

SFZ_NOTE_LETTER_OFFSET = {'a': 9, 'b': 11, 'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7}


def sfz_note_to_midi_key(sfz_note, german=False):
    accidental = 0

    if '#' in sfz_note[1:] or '♯' in sfz_note:
        accidental = 1
    elif 'b' in sfz_note[1:] or '♭' in sfz_note:
        accidental = -1

    letter = sfz_note[0].lower()

    if german:
        # TODO: Handle sharps (e.g. "Fis") and flats (e.g. "Es")
        if letter == 'b':
            accidental = -1
        if letter == 'h':
            letter = 'b'

    octave = int(sfz_note[-1])
    return max(0, min(127, SFZ_NOTE_LETTER_OFFSET[letter] + ((octave + 1) * 12) + accidental))


def freq_to_cutoff(param):
    return 127. * max(0, min(1, math.log(param / 130.) / 5)) if param else None


KNOWN_OPCODES = [
    'ampeg_attack',
    'ampeg_decay',
    'ampeg_hold',
    'ampeg_sustain',
    'ampeg_release',
    'cutoff',
    'fillfo_freq',
    'amplfo_freq',
    'pitchlfo_freq',
    'sample',
    'lokey',
    'hikey',
    'pitch_keycenter',
    'lovel',
    'hivel',
    'pan',
    'volume',
    'key',
    'effect1',
    'effect2',
    'transpose',
    'pitch_keytrack',

    # Ignored, for now
    'group',
    'off_by',
    'loop_mode',
    'resonance',
    'ampeg_delay',
    'pitchlfo_delay',
    'pitchlfo_depth',
    'fillfo_delay',
    'fillfo_depth',
    'amplfo_delay',
    'amplfo_depth',
    'pitcheg_delay',
    'pitcheg_attack',
    'pitcheg_decay',
    'pitcheg_hold',
    'pitcheg_release',
    'pitcheg_sustain',
    'pitcheg_depth',
    'fileg_delay',
    'fileg_attack',
    'fileg_decay',
    'fileg_hold',
    'fileg_sustain',
    'fileg_depth',
    'fileg_release',
    'tune'

]


class Group():
    def __init__(self):
        self.opcodes = {}
        self.regions = []


class Region():
    def __init__(self, sfz_path):
        self.opcodes = {}
        self.sfz_path = sfz_path

    def get_sample_path(self):
        dir = os.path.dirname(self.sfz_path)
        return '/'.join([dir, self.opcodes['sample'].replace('\\', '/')])

    def convert_numbers(self):
        for key, value in self.opcodes.items():
            if value.isdigit():
                self.opcodes[key] = int(value)
            else:
                try:
                    fval = float(value)
                    self.opcodes[key] = fval
                except Exception:
                    pass


class SFZParser(object):
    rx_section = re.compile('^<([^>]+)>\\s?')

    def __init__(self, sfz_path, encoding=None, debug=False, **kwargs):

        self.encoding = encoding
        self.debug = debug
        self.sfz_path = sfz_path
        anon_grp = Group()
        self.groups = [anon_grp]

        with open(sfz_path, encoding=self.encoding or 'utf-8-sig') as sfz:
            self.parse(sfz)

    def add_key_value(self, in_region, key, value):
        if key not in KNOWN_OPCODES:
            raise ValueError('Unknown opcode: ', f'[{key}]')
        if in_region:
            self.groups[-1].regions[-1].opcodes[key] = value
        else:
            self.groups[-1].opcodes[key] = value

    def parse(self, sfz):
        in_region = False
        value = None

        for linenum, line in enumerate(sfz):
            line = line.strip()
            if self.debug:
                elogger.info(linenum, line)

            if not line:
                continue

            if line.startswith('//'):
                continue

            while line:
                match = self.rx_section.search(line)
                if match:
                    name = match.group(1).strip()
                    if name == 'group':
                        self.groups.append(Group())
                        in_region = False
                    elif name == 'region':
                        self.groups[-1].regions.append(Region(self.sfz_path))
                        in_region = True
                    else:
                        raise ValueError("Unknown header:", name)
                    line = line[match.end():].lstrip()
                elif "=" in line:
                    line, _, value = line.rpartition('=')
                    if '=' in line:
                        line, key = line.rsplit(None, 1)
                        self.add_key_value(in_region, key, value)
                        value = None
                elif value:
                    line, key = None, line
                    self.add_key_value(in_region, key, value)

                else:
                    if line.startswith('//'):
                        print("Warning: inline comment")
                    # ignore garbage
                    break

    def create_sfz(self):
        sfz = SFZ(self.sfz_path)
        for g in self.groups:
            if len(g.opcodes) > 0:
                for region in g.regions:
                    for key, value in g.opcodes.items():
                        if key not in region.opcodes:
                            region.opcodes[key] = value
                    sfz.add_region(region)
        return sfz


class SFZ():
    def __init__(self, path):
        self.sfz_path = path
        self.note_map = {}
        self.regions = []

    def add_region(self, region):
        region.convert_numbers()
        self.regions.append(region)
        op = region.opcodes
        lovel = op.get('lovel', 1)
        hivel = op.get('hivel', 127)

        if 'key' in region.opcodes:
            self.add(op['key'], op['key'], lovel, hivel, region)
        else:
            lokey = op.get('lokey', 0)
            hikey = op.get('hikey', 0)
            self.add(lokey, hikey, lovel, hivel, region)

    def get_sound_info(self, note, velocity):
        vmap = self.note_map.get(note, None)
        if vmap is None:
            elogger.error("No velocity map for note:", note, self.sfz_path)
            return []
        else:
            sinfo = vmap.get(velocity, None)
            if sinfo is None:
                elogger.error("No entry for note, velocity:", note, velocity, self.sfz_path)
                return []
            return sinfo

    def add(self, lokey, hikey, lovel, hivel, region):
        for key in range(int(lokey), int(hikey) + 1):
            if key not in self.note_map:
                self.note_map[key] = {}
            vel_map = self.note_map[key]
            for vel in range(int(lovel), int(hivel) + 1):
                if vel not in vel_map:
                    vel_map[vel] = []
                regions = vel_map[vel]
                regions.append(region)


if __name__ == '__main__':

    parser = SFZParser('/Users/shiva/sounds/DSKMusic/sfz/DSK Music - Organs/Big.sfz', debug=True)
    sfz = parser.create_sfz()
    print(sfz.get_sound_info(60, 60))
    pass
