from typing import Tuple, Dict

from music21 import key, meter, instrument, stream

from app_models.audio_player import AudioPlayer
from app_models.event_observable import Observable
from music21_addons.onetrack import onetrack_parser, onetrack_to_part


class Track():
    def __init__(self, multitrack, timesig, tkey, imap):
        self.multitrack = multitrack
        self.timesig = timesig
        self.key = tkey
        self.muted = Observable(False)
        self.soloed = Observable(False)
        self.instrument = Observable('')
        self.tiny = Observable('')
        self.imap = imap
        self.parser = onetrack_parser()
        self.on_item = Observable(None)

    def flatten_instruments(self, gm_inst: Dict[Tuple[str, str], int]):
        return [t0 + ':' + t1 for t0, t1 in gm_inst.keys()]

    def get_instrument_names(self):
        return self.flatten_instruments(self.imap)

    def get_part(self) -> Tuple[stream.Part, Dict]:
        part, notemap = onetrack_to_part(self.tiny.value, self.parser, id=self)
        part.insert(0, self.get_instrument())
        return part, notemap

    def get_instrument(self) -> instrument.Instrument:
        [group, name] = self.instrument.value.split(':')
        inst = instrument.Instrument(self.instrument.value)
        inst.midiProgram = self.imap[(group, name)]
        return inst
        # return instrument.instrumentFromMidiProgram(self.imap[(group, name)])

    def now_playing(self, lobj):
        if lobj:
            self.on_item.value = lobj.location()
        else:
            self.on_item.value = None


class MultiTrack():
    def __init__(self, synth, skey=key.Key('C'), timesig=meter.TimeSignature('4/4')):
        self.key = Observable(skey)
        self.timesig = Observable(timesig)

        self.tracks = []
        self.player = AudioPlayer(synth)

    def add_track(self):
        new_track = Track(self, self.timesig, self.key,
                          self.player.sequencer.synth.get_instrument_map())
        self.tracks.append(new_track)
        new_track.instrument.value = new_track.get_instrument_names()[0]

    def play(self):
        self.player.play_or_pause(self.tracks, self.timesig)

    def stop(self):
        self.player.stop()
