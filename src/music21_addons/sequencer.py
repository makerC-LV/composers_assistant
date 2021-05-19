import threading
from threading import Thread
from abc import ABC, abstractmethod
from typing import Dict, Tuple

import fluidsynth
import mido
import pygame
from mido import Message
from music21 import tempo, note, chord
from sortedcontainers import SortedDict

from utils import elogger
from utils.midi_instrument_defs import get_flat_gm_instrument_map


class Synth(ABC):
    @abstractmethod
    def note_on(self, notenum, chan, velocity):
        pass

    @abstractmethod
    def note_off(self, notenum, chan, velocity):
        pass

    @abstractmethod
    def program_change(self, chan, inst):
        pass

    @abstractmethod
    def get_instrument_map(self) -> Dict[Tuple[str, str], int]:
        return get_flat_gm_instrument_map()


class TextSynth(Synth):

    def note_on(self, notenum, chan, velocity):
        elogger.debug("note_on:", notenum, chan, velocity)

    def note_off(self, notenum, chan, velocity):
        elogger.debug("note_off:", notenum, chan, velocity)

    def program_change(self, chan, inst):
        elogger.debug("program_change", chan, inst)


class PyFluidSynth(Synth):
    fs = None
    sfid = None

    @classmethod
    def init_synth(cls):
        if cls.fs is not None:
            return
        cls.fs = fluidsynth.Synth()
        cls.fs.start()
        cls.sfid = cls.fs.sfload('/Users/shiva/sounds/soundfonts/FluidR3_GM.sf2')

    def __init__(self):
        PyFluidSynth.init_synth()

    def note_on(self, notenum, chan, velocity):
        elogger.debug("note_on:", notenum, chan, velocity)
        PyFluidSynth.fs.noteon(chan, notenum, velocity)

    def note_off(self, notenum, chan, velocity):
        elogger.debug("note_off:", notenum, chan, velocity)
        PyFluidSynth.fs.noteoff(chan, notenum)

    def program_change(self, chan, inst):
        elogger.debug("program_change", chan, inst)
        bank = 0
        preset = inst
        PyFluidSynth.fs.program_select(chan, PyFluidSynth.sfid, bank, preset)


class MidoSynth(Synth):
    _instrument_map = None

    @classmethod
    def configure_instrument_map(cls, instrument_map):
        MidoSynth._instrument_map = instrument_map

    def __init__(self, debug=False):
        self.debug = debug
        mido.set_backend('mido.backends.pygame')
        pname = mido.get_output_names()[0]
        self.port = mido.open_output(pname)

    def note_on(self, notenum, chan, velocity):
        if self.debug:
            elogger.info("note_on:", notenum, chan, velocity)
        msg = Message('note_on', note=notenum, channel=chan, velocity=velocity)
        self.port.send(msg)

    def note_off(self, notenum, chan, velocity):
        if self.debug:
            elogger.info("note_off:", notenum, chan, velocity)
        msg = Message('note_off', note=notenum, channel=chan, velocity=velocity)
        self.port.send(msg)

    def program_change(self, chan, inst):
        if self.debug:
            elogger.info("program_change", chan, inst)
        msg = Message('program_change', channel=chan, program=inst)
        self.port.send(msg)

    def get_instrument_map(self) -> Dict[Tuple[str, str], int]:
        return MidoSynth._instrument_map


def noop(*args):
    pass


class MySequencer():
    def __init__(self, synth):
        self.synth = synth
        self.playing = False
        self.pos = 0
        self.length = 0
        self.pos_lock = threading.Lock()
        self.play_lock = threading.Lock()

    def play(self, score, tempo, now_playing=noop, progress_update=noop, finished_cb=noop):
        self.now_playing = now_playing
        self.progress_update = progress_update
        self.finished_cb = finished_cb
        self.to_play = self.get_to_play(score, tempo)
        self.channel_inst = [-1] * 16
        t, _ = self.to_play.peekitem(-1)
        self.length = int(t * 1000)
        self.on_items = {}
        self.start()

    def start(self):

        self.playing = True

        def continue_playing():
            to_play_ptr = self.move_to_pos()
            last_time = pygame.time.get_ticks()
            while self.playing and to_play_ptr < len(self.to_play):
                self.play_lock.acquire()
                t, to_play_list = self.to_play.peekitem(to_play_ptr)
                now = pygame.time.get_ticks()
                time_since_start = now - last_time
                time_to_wait = int(t * 1000 - (self.pos + time_since_start))
                if time_to_wait <= 0:
                    self.pos = int(t * 1000)
                    self.process(to_play_list, True)
                    to_play_ptr += 1
                    last_time = pygame.time.get_ticks()
                else:
                    pygame.time.wait(time_to_wait)
                self.play_lock.release()
            self.stop_all_playing_notes()
            if to_play_ptr >= len(self.to_play):
                self.stop()

        thr = Thread(target=continue_playing)
        thr.start()

    def move_to_pos(self):
        to_play_ptr = 0
        t, to_play_list = self.to_play.peekitem(to_play_ptr)
        while t * 1000 < self.pos:
            self.process(to_play_list, False)
            to_play_ptr += 1
            t, _ = self.to_play.peekitem(to_play_ptr)
        return to_play_ptr

    def process(self, to_play_list, send_notes):
        for ncr, is_on, inst, chan in to_play_list:
            self.process_one(ncr, is_on, inst, chan, send_notes)
        if (send_notes):
            now_on = [ncr for (ncr, inst, chan) in self.on_items.values()]
            thr = Thread(target=self.now_playing, args=[now_on])
            thr.start()
            thr = Thread(target=self.update_progress, args=[self.pos, self.length])
            thr.start()

    def update_progress(self, pos, length):
        self.pos_lock.acquire()
        self.progress_update(pos, length)
        self.pos_lock.release()

    def process_one(self, ncr, is_on, inst, chan, send_notes):
        # elogger.info("processing:", ncr, is_on, send_notes)
        if self.channel_inst[chan] != inst:
            self.synth.program_change(chan, inst)
            self.channel_inst[chan] = inst
        if send_notes:
            if is_on:
                note_fn = self.synth.note_on
                on_fn = self.add_to_on
            else:
                note_fn = self.synth.note_off
                on_fn = self.remove_from_on

            if isinstance(ncr, note.Note):
                note_fn(ncr.pitch.midi, chan, ncr.volume.velocity)
                on_fn(id(ncr), ncr, inst, chan)
            elif isinstance(ncr, chord.Chord):
                for p in ncr.pitches:
                    note_fn(p.midi, chan, ncr.volume.velocity)
                on_fn(id(ncr), ncr, inst, chan)

    def add_to_on(self, id, ncr, inst, chan):
        # elogger.info(self.on_items)
        self.on_items[id] = (ncr, inst, chan)

    def remove_from_on(self, id, ncr, inst, chan):
        # elogger.info(self.on_items)
        if id in self.on_items:
            self.on_items.pop(id)

    def pause(self):
        if self.playing:
            self.playing = False

    def unpause(self):
        if not self.playing:
            self.playing = True
            self.start()

    def stop(self):
        self.playing = False
        self.play_lock.acquire()
        self.pos_lock.acquire()
        self.play_lock.release()
        self.pos_lock.release()
        self.set_pos(0)
        self.finished_cb()

    def get_pos(self):
        return self.pos

    def set_pos(self, pos):
        self.pos = pos

    def rewind(self):
        self.set_pos(0)

    def get_to_play(self, score, bpm):
        sd = SortedDict()
        mm = tempo.MetronomeMark(number=bpm)
        # mm.durationToSeconds(offset)
        unused_channels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
        for part in score.parts:
            inst, chan = self.get_instrument_number(part, unused_channels)
            for ncr in part.flat.getElementsByClass(['Note', 'Chord', 'Rest']):
                sec_start = mm.durationToSeconds(ncr.offset)
                sec_end = sec_start + mm.durationToSeconds(ncr.duration)
                self.add_to_dict_list(sd, sec_start, (ncr, True, inst, chan))
                self.add_to_dict_list(sd, sec_end, (ncr, False, inst, chan))

        return sd

    def get_instrument_number(self, part, unused_channels):
        inst = part.getElementsByClass('Instrument')[0]
        inum = inst.midiProgram
        chan = unused_channels[0]
        unused_channels.remove(chan)
        return inum, chan

    def add_to_dict_list(self, sd, key, param):
        if key in sd:
            sd[key].append(param)
        else:
            sd[key] = [param]

    def stop_all_playing_notes(self):
        on = [(ncr, inst, chan) for (ncr, inst, chan) in self.on_items.values()]
        for (ncr, inst, chan) in on:
            self.process_one(ncr, False, inst, chan, True)
        self.on_items.clear()
