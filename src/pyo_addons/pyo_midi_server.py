import time

from mido import Message
from pyo import MToF, Sig, Server, RawMidi

from utils import elogger
from typing import Dict

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
            elogger.info("Play: ", self.name)
        self.is_playing = True
        for arg in self.playables:
            arg.play()
        if self.output is not None:
            self.output.out()

    def stop(self):
        if self.debug:
            elogger.info("Stop: ", self.name)
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
                elogger.info("Program change on chan:", self.channelnum, " value:", new_program)
                if self.current_inst is not None:
                    self.insts[self.current_program] = self.current_inst
                if new_program in self.insts:
                    self.current_inst = self.insts[new_program]
                else:
                    self.current_inst = self.midisetup.create_inst(new_program)
                    self.insts[new_program] = self.current_inst
                self.current_program = new_program
        except Exception:
            elogger.exception()


class MidiSetup():

    def __init__(self, inst_programs):
        self.channels = {i: MidiChannel(self, i) for i in INST_CHANNELS}
        self.inst_programs = inst_programs

    def create_inst(self, program):
        return self.inst_programs[program]()


def voice_generator(voice_class):
    def generate():
        return voice_class(True)

    return generate


def instrument_generator(polyphony, voice_generator):
    def generate():
        return PolyphonicInstrument(polyphony, voice_generator, True)

    return generate


def run_server(midi_setup, inst_init_func=lambda *args: None):
    s = Server()
    s.setMidiInputDevice(99)  # Open all input devices.
    s.boot()
    s.start()
    try:
        inst_init_func()
    except Exception:
        elogger.exception()
        s.stop()
        time.sleep(5)
        exit()

    def event(status, data1, data2):
        try:
            # elogger.info(status, data1, data2)
            if status >= 0xC0 and status <= 0xCF:  # prog change
                m = Message.from_bytes([status, data1])
                ch = m.channel
                pg = m.program
                midi_setup.channels[ch].pchange(pg)
            else:
                m = Message.from_bytes([status, data1, data2])
                if m.type == "note_on":
                    midi_setup.channels[m.channel].note_on(m.note, m.velocity)
                elif m.type == "note_off":
                    midi_setup.channels[m.channel].note_off(m.note, m.velocity)
                elif m.type == "pitchwheel":
                    midi_setup.channels[m.channel].pitchwheel(m.pitch)
                else:
                    elogger.warn("Ignoring: ", m)
        except Exception:
            elogger.exception()

    # Needs to be global so it doesn't get garbage collected
    global midi_receiver
    midi_receiver = RawMidi(event)

    return s


if __name__ == '__main__':
    from pyo_addons.sfz_instrument import SFZVoice, get_sfz_map_from_config, sfz_voice_generator

    # sine = instrument_generator(4, voice_generator(SineVoice))
    # INST_PROGRAMS = {1: sine, 2: sine, 3: sine, 4: sine}

    map = get_sfz_map_from_config('../config/dskconfig.json')
    INST_PROGRAMS = {i: instrument_generator(4, sfz_voice_generator(name)) for i, name in enumerate(map.keys())}
    ms = MidiSetup(INST_PROGRAMS)
    s = run_server(ms, lambda *args: SFZVoice.read_sounds(map))
    # s = run_server(ms)
    print('Here')

    s.gui(locals())
