import logging
import time
from typing import Dict, Callable, Optional, Tuple

from pyo import MToF, Sig, Server

from music21_addons.sequencer import Synth

logger = logging.getLogger(__name__)

INST_CHANNELS = [x for x in range(0, 9)] + [x for x in range(10, 16)]

midi_receiver = None


class Voice():
    def __init__(self, name, debug=False):
        self.name = name
        self.debug = debug
        self.playables = []
        self.output = None
        self.note = 0
        self.pitch_bend = 0
        self.velocity = 0
        self.is_playing = False

    def set_playables(self, *args):
        for arg in args:
            self.playables.append(arg)

    def get_freq(self, ):  # TODO: Implement bend
        return MToF(Sig(self.note))

    def get_amplitude(self):
        return self.velocity / 128.0

    def play(self):
        if self.debug:
            logger.info("Play: %s", self.name)
        self.is_playing = True
        for arg in self.playables:
            arg.play()
        if self.output is not None:
            self.output.out()

    def stop(self):
        if self.debug:
            logger.info("Stop: %s", self.name)
        for arg in self.playables:
            arg.stop()
        if self.output is not None:
            self.output.stop()
        self.is_playing = False


class PolyphonicInstrument():
    def __init__(self, poly=1, voice_generator=None, debug=False):
        self.debug = debug
        self.voices = [None] * poly
        self.voice_generator = voice_generator

    def note_on(self, note, velocity):
        if velocity == 0:
            self.note_off(note, velocity)
            return
        slot = self.find_free_voice(note)
        if slot is not None:
            slot.note = note
            slot.velocity = velocity
            slot.play()

    def note_off(self, note, velocity):
        slots = self.find_voices_playing_note(note)
        for slot in slots:
            slot.stop()

    def find_free_voice(self, note):
        for i, voice in enumerate(self.voices):
            if voice is None:
                self.voices[i] = self.voice_generator()
                return self.voices[i]
            elif not voice.is_playing:
                return self.voices[i]
        return None

    def find_voices_playing_note(self, note):
        voices = []
        for i, voice in enumerate(self.voices):
            if voice is not None and voice.note == note:
                voices.append(voice)
        return voices


class MidiChannel():
    def __init__(self, midisetup, channelnum: int):
        if channelnum not in INST_CHANNELS:
            raise ValueError("Instrument channel cannot have the number ", channelnum)
        self.midisetup = midisetup
        self.channelnum = channelnum
        self.insts = {}  # type: Dict[int, PolyphonicInstrument]
        self.current_program = -1
        self.current_inst = None

    def note_on(self, note, velocity):
        self.current_inst.note_on(note, velocity)

    def note_off(self, note, velocity):
        self.current_inst.note_off(note, velocity)

    def pchange(self, new_program):
        try:
            # new_program = self.prog.get()
            if new_program != self.current_program:
                logger.info("Program change on chan: %s  value: %s", self.channelnum, new_program)
                if self.current_inst is not None:
                    self.insts[self.current_program] = self.current_inst
                if new_program in self.insts:
                    self.current_inst = self.insts[new_program]
                else:
                    self.current_inst = self.midisetup.create_inst(new_program)
                    self.insts[new_program] = self.current_inst
                self.current_program = new_program
        except Exception as e:
            logger.error(e, exc_info=True)


class PyoSynth(Synth):
    _instrument_map = None
    _instrument_creator_map = None
    pyo_server = None

    @classmethod
    def configure(cls, inst_creator_map: Dict[int, Callable], load_instruments_fn=lambda *args: None):
        PyoSynth._instrument_creator_map = inst_creator_map
        if PyoSynth.pyo_server is None:
            PyoSynth.pyo_server = Server()
            PyoSynth.pyo_server.setMidiInputDevice(99)  # Open all input devices.
            PyoSynth.pyo_server.boot()
            PyoSynth.pyo_server.start()
        try:
            load_instruments_fn()
        except Exception as e:
            logger.exception(e, exc_info=True)

    @classmethod
    def configure_instrument_map(cls, instrument_map: Dict[Tuple[str, str], int]):
        PyoSynth._instrument_map = instrument_map

    def __init__(self):
        self.channels = {i: MidiChannel(self, i) for i in INST_CHANNELS}

    def note_on(self, notenum, chan, velocity):
        self.channels[chan].note_on(notenum, velocity)

    def note_off(self, notenum, chan, velocity):
        self.channels[chan].note_off(notenum, velocity)

    def program_change(self, chan, inst):
        self.channels[chan].pchange(inst)

    def get_instrument_map(self) -> Optional[Dict[Tuple[str, str], int]]:
        return PyoSynth._instrument_map

    def create_inst(self, program):
        return PyoSynth._instrument_creator_map[program]()

    @classmethod
    def stop(cls):
        PyoSynth.pyo_server.stop()


def voice_generator(voice_class):
    def generate():
        return voice_class(True)

    return generate


def instrument_generator(polyphony, voice_generator):
    def generate():
        return PolyphonicInstrument(polyphony, voice_generator, True)

    return generate


def run_server(midi_setup, inst_init_func=lambda *args: None):
    pyo_server = Server()
    pyo_server.setMidiInputDevice(99)  # Open all input devices.
    pyo_server.boot()
    pyo_server.start()
    try:
        inst_init_func()
    except Exception as e:
        logger.exception(e, exc_info=True)
        pyo_server.stop()
        time.sleep(5)
        exit()

    return pyo_server
