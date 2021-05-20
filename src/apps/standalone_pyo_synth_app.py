from typing import Optional

from mido import Message
from pyo import RawMidi

from pyo_addons.embedded_pyo_synth import instrument_generator, PyoSynth
import logging

logger = logging.getLogger(__name__)

# Global
pyo_synth = None  # type: Optional[PyoSynth]
midi_receiver = None  # type: Optional[RawMidi]


def event(status, data1, data2):
    global pyo_synth
    try:
        # elogger.info(status, data1, data2)
        if status >= 0xC0 and status <= 0xCF:  # prog change
            m = Message.from_bytes([status, data1])
            ch = m.channel
            pg = m.program
            pyo_synth.program_change(ch, pg)
        else:
            m = Message.from_bytes([status, data1, data2])
            if m.type == "note_on":
                pyo_synth.note_on(m.note, m.channel, m.velocity)
            elif m.type == "note_off":
                pyo_synth.note_off(m.note, m.channel, m.velocity)
            elif m.type == "pitchwheel":
                # pyo_synth.pitchwheel(m.channel, m.pitch)
                logger.warning("Ignoring: %s", m)
            else:
                logger.warning("Ignoring: %s", m)
    except Exception as e:
        logger.error(e, exc_info=True)


if __name__ == '__main__':
    from pyo_addons.sfz_instrument import SFZVoice, get_sfz_map_from_config, sfz_voice_generator, read_sfz_config

    # sine = instrument_generator(4, voice_generator(SineVoice))
    # INST_PROGRAMS = {1: sine, 2: sine, 3: sine, 4: sine}

    map = get_sfz_map_from_config('../config/dskconfig.json')
    INST_PROGRAMS = {i: instrument_generator(4, sfz_voice_generator(name)) for i, name in enumerate(map.keys())}
    PyoSynth.configure(INST_PROGRAMS, lambda *args: SFZVoice.read_sounds(map))
    PyoSynth.configure_instrument_map(read_sfz_config('../config/dskconfig.json'))

    # Needs to be global so it doesn't get garbage collected
    pyo_synth = PyoSynth()
    midi_receiver = RawMidi(event)

    PyoSynth.pyo_server.gui(locals())
