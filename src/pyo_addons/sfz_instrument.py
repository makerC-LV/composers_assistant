import json
import os
import time
from threading import Thread
from typing import Dict, Tuple

from pyo import SndTable, DataTable, Adsr, LFO, TableRead, Pan, ButLP, Freeverb, Chorus

from pyo_addons.pyo_midi_server import Voice
from pyo_addons.sfz_parser import SFZParser
import numpy as np

from utils import elogger
from pyo_addons.sfz_parser import SFZ


class SFZVoice(Voice):
    silencetable = None
    sfz_map = {}  # type: Dict[str, SFZ]

    @classmethod
    def read_sounds(cls, name_path_map):
        for name, path in name_path_map.items():
            if name not in SFZVoice.sfz_map:
                parser = SFZParser(path)
                elogger.info("Loading ", path)
                sfz = parser.create_sfz()
                SFZVoice.sfz_map[name] = sfz
                for region in sfz.regions:
                    path = region.get_sample_path()
                    # elogger.info("reading sample:", path)
                    region.sndtable = SndTable(path)

    def __init__(self, name, debug=False):
        super().__init__(name, debug=debug)
        if SFZVoice.silencetable is None:
            SFZVoice.silencetable = DataTable(size=16)
        self.semitone_multiplier = float(np.power(2, 1 / 12))
        self.adsr = Adsr(decay=50.11)
        self.amplfo = LFO(type=7, mul=0.01, add=1)  # type - Modulated sine
        self.pitchlfo = LFO(type=7, add=1, mul=0.0001)  # type - Modulated sine
        self.osc = TableRead(table=SFZVoice.silencetable, freq=self.pitchlfo, mul=self.amplfo)
        self.pan = Pan(self.osc, mul=self.adsr)
        self.fillfo = LFO(type=7, add=1, mul=0.01)
        self.filter = ButLP(self.pan, freq=self.fillfo)
        self.reverb = Freeverb(self.filter)
        self.chorus = Chorus(self.reverb)
        self.set_playables(self.adsr, self.amplfo, self.osc, self.pitchlfo, self.pan, self.fillfo, self.filter,
                           self.reverb)
        self.output = self.chorus

    def get_region(self):
        sfz = SFZVoice.sfz_map[self.name]
        rlist = sfz.get_sound_info(self.note, self.velocity)
        if len(rlist) == 0:
            return None
        if len(rlist) > 1:
            elogger.error("More than one region", self.note, self.velocity)
        return rlist[0]

    def play(self):
        r = self.get_region()
        if r is None:
            return
        t = r.sndtable
        tfreq = t.getRate()
        self.osc.table = t
        self.pitchlfo.add = self.calc_freq(r.opcodes, tfreq)
        # self.osc.freq = self.calc_freq(r.opcodes, tfreq)
        self.osc.mul = self.calc_volume(r.opcodes)
        self.fillfo.add = r.opcodes.get('cutoff', 15000)  # default is filter disabled
        # self.filter.freq = r.opcodes.get('cutoff', 15000)  # default is filter disabled
        self.pan.pan = 0.5 + r.opcodes.get('pan', 0) / 200
        self.adsr.attack = r.opcodes.get('ampeg_attack', 0)
        self.adsr.decay = r.opcodes.get('ampeg_decay', 0)
        self.adsr.sustain = r.opcodes.get('ampeg_sustain', 100) / 100
        self.adsr.release = self.calc_release(r.opcodes, t.getDur())
        self.adsr.dur = r.opcodes.get('ampeg_hold', 0)
        self.amplfo.freq = r.opcodes.get('amplfo_freq', 0)
        self.pitchlfo.freq = r.opcodes.get('pitchlfo_freq', 0)
        self.fillfo.freq = r.opcodes.get('fillfo_freq', 0)
        self.reverb.bal = r.opcodes.get('effect1', 0) / 100
        self.chorus.bal = r.opcodes.get('effect2', 0) / 100
        super().play()

    def stop(self):
        rel = self.adsr.release
        self.adsr.stop()
        Thread(target=lambda *args: self.delay_stop_non_adsr(rel)).start()

    def delay_stop_non_adsr(self, delay):
        time.sleep(delay)
        super().stop()
        self.amplfo.reset()
        self.fillfo.reset()
        self.pitchlfo.reset()

    def calc_freq(self, opcodes, tfreq):
        pitch = opcodes.get('key', opcodes.get('pitch_keycenter'))
        transpose = opcodes.get('transpose', 0)
        pitch_change_per_semitone = opcodes.get('pitch_keytrack', 100) / 100
        semitones = pitch_change_per_semitone * (self.note - (pitch + transpose))
        if semitones == 0:
            return tfreq
        return float(tfreq * np.power(self.semitone_multiplier, semitones))

    def calc_volume(self, opcodes):
        db_vol = opcodes.get('volume', 0)
        volmul = np.power(10, db_vol / 10)
        return self.amplfo * volmul

    def calc_release(self, opcodes, dur):
        attack = self.adsr.attack
        decay = self.adsr.decay
        return max(0.001, min(dur - (attack + decay), opcodes.get('ampeg_release', 0.001)))


def sfz_voice_generator(name):
    def generate():
        return SFZVoice(name, True)

    return generate


def get_sfz_map(dir, save_file=None):
    map = {}
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.endswith('.sfz'):
                path = root + '/' + file
                last_dir = os.path.basename(root)
                map[last_dir + ':' + file] = path
    if save_file is not None:
        with open(save_file, 'w') as cf:
            json.dump(map, cf)
    return map


def get_flat_sfz_map(map) -> Dict[Tuple[str, str], int]:
    fm = {}
    for i, (key, value) in enumerate(map.items()):
        [group, name] = key.split(':')
        fm[(group, name)] = i
    return fm


def get_sfz_map_from_config(file) -> Dict[str, int]:
    with open(file, 'r') as cf:
        map = json.load(cf)
    return map


def read_sfz_config(file) -> Dict[Tuple[str, str], int]:
    map = get_sfz_map_from_config(file)
    return get_flat_sfz_map(map)

# get_sfz_map('/Users/shiva/sounds/DSKMusic/sfz')
