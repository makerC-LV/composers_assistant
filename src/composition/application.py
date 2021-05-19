import logging
import threading
from typing import Any, Dict, Tuple

from music21 import stream, key, meter, instrument

from music21_addons.onetrack import onetrack_parser, onetrack_to_part, part_to_onetrack
from music21_addons.sequencer import MySequencer, PyFluidSynth

logger = logging.getLogger(__name__)


class Event(object):
    def __init__(self):
        self.callbacks = []

    def notify(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def register(self, callback):
        self.callbacks.append(callback)
        return callback


class Observable(object):
    def __init__(self, v: Any, debug=False):
        self._value = v
        self.debug = debug
        self.changed = Event()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        old_value = self._value
        if old_value != v:
            self._value = v
            if self.debug:
                logger.info("Setting observable value: (thread:%s) %s", threading.get_ident(), v)
            self.changed.notify(old_value, v)


class Track():
    def __init__(self, timesig, tkey, imap):
        self.timesig = timesig
        self.key = tkey
        self.muted = Observable(False)
        self.soloed = Observable(False)
        self.instrument = Observable('')
        self.tiny = Observable('')
        self.imap = imap
        self.menu = self.build_menu_map()
        self.parser = onetrack_parser()
        self.on_item = Observable(None)

    def flatten_instruments(self, gm_inst: Dict[Tuple[str, str], int]):
        return [t0 + ':' + t1 for t0, t1 in gm_inst.keys()]

    def get_instrument_names(self):
        return self.flatten_instruments(self.imap)

    def get_part(self) -> Tuple[stream.Part, Dict]:
        part, notemap = onetrack_to_part(self.tiny.value, self.parser, id=self)
        # tnc = tinyNotation.Converter(self.tiny.value)
        # tnc.parse()
        # part = tnc.stream
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

    def build_menu_map(self):
        m = {
            'aaa': self.aaa,
            'track': {
                'Transpose': {str(x): self.transpose_fn(x) for x in range(-12, 12)},
                'Create copy track': self.create_copy_track,
                'Create chord track': self.create_chord_track,
                'Create bass track': self.create_bass_track,
                'Create drum track': self.create_drum_track,

            },
            'selection': {
                'Replace with silence': self.replace_sel_with_silence,
                'Open variations window...': self.open_variations_window,
                'Open embellishments window...': self.open_embellishments_window,
            }
        }
        return m

    def aaa(self):
        pass

    def replace_sel_with_silence(self):
        pass

    def transpose_fn(self, semitones):
        def tp():
            p, m = self.get_part()
            p.transpose(semitones, inPlace=True)
            self.tiny.value = part_to_onetrack(p)

        return tp

    def create_copy_track(self):
        pass

    def open_embellishments_window(self):
        pass

    def open_variations_window(self):
        pass

    def create_drum_track(self):
        pass

    def create_bass_track(self):
        pass

    def create_chord_track(self):
        pass


APSTATE_PAUSED = 'Paused'
APSTATE_STOPPED = 'Stopped'
APSTATE_PLAYING = 'Playing'


class AudioPlayer():
    def __init__(self):
        self.state = Observable(APSTATE_STOPPED)
        self.tempo = Observable(60)
        self.length = Observable(60000)
        self.cue_pos = Observable(0)
        # self.sequencer = MySequencer(MidoSynth(True))
        self.sequencer = MySequencer(PyFluidSynth())

    def play_or_pause(self, tracks, timesig):
        if self.state.value == APSTATE_PLAYING:
            self.pause()
        elif self.state.value == APSTATE_PAUSED:
            self.unpause()
        elif self.state.value == APSTATE_STOPPED:
            self.play(tracks, timesig, self.tempo.value)

    def play(self, tracks, timesig, bpm):
        parts = []
        self.tracks = tracks
        solo_tracks = [t for t in tracks if t.soloed.value]
        solo_track = None if len(solo_tracks) == 0 else solo_tracks[0]
        for t in tracks:
            part = t.get_part()
            if t.muted.value or (solo_track and t != solo_track):
                part = (part[0].template(), {})  # Remove all notes and fill with rests, empty map
            parts.append(part)
        if len(parts) > 0:
            cmap = {}
            score = stream.Score()
            for p, map in parts:
                score.insert(0, p)
                cmap.update(map)

            def now_playing(playing_list):
                for obj in playing_list:
                    (lobj, track) = cmap[id(obj)]
                    track.now_playing(lobj)

            def progress_update(position, length):
                self.cue_pos.value = position
                self.length.value = length

            self.sequencer.play(score, bpm, now_playing, progress_update, self.finished)
            self.state.value = APSTATE_PLAYING

    # def monitor(self):
    #     while self.sp and self.sp.pygame.mixer.music.get_busy():
    #         print("pos", self.sp.pygame.mixer.music.get_pos())
    #         self.sp.pygame.time.wait(100)
    #     if self.state.value == APSTATE_PLAYING:  # Playback ended
    #         self.stop()

    def pause(self):
        if self.state.value == APSTATE_PLAYING:
            self.state.value = APSTATE_PAUSED
            self.sequencer.pause()

    def unpause(self):
        if self.state.value == APSTATE_PAUSED:
            self.state.value = APSTATE_PLAYING
            self.sequencer.unpause()

    def stop(self):
        self.sequencer.stop()
        self.state.value = APSTATE_STOPPED

    def finished(self, dummy=None):
        # print("Finished")
        self.cue_pos.value = 0
        self.state.value = APSTATE_STOPPED
        if self.tracks:
            for t in self.tracks:
                t.now_playing(None)


class MultiTrack():
    def __init__(self, gui):
        self.gui = gui
        self.key = Observable(key.Key('C'))
        self.timesig = Observable(meter.TimeSignature('4/4'))

        self.tracks = []
        self.player = AudioPlayer()

    def add_track(self):
        new_track = Track(self.timesig, self.key,
                          self.player.sequencer.synth.get_instrument_map())
        self.tracks.append(new_track)
        self.gui.track_added(self, new_track)
        new_track.instrument.value = new_track.get_instrument_names()[0]

    def play(self):
        self.player.play_or_pause(self.tracks, self.timesig)

    def stop(self):
        self.player.stop()
