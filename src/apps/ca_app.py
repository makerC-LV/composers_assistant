from gui.main_window import main_window
from utils.midi_instrument_defs import get_flat_gm_instrument_map

if __name__ == '__main__':
    # from music21_addons.sequencer import MidoSythn
    # MidoSynth.configure_instrument_map(read_sfz_config('../config/dskconfig.json'))
    # main(MidoSynth())

    # from pyo_addons.sfz_instrument import read_sfz_config, get_sfz_map_from_config, sfz_voice_generator, SFZVoice
    # from pyo_addons.embedded_pyo_synth import instrument_generator, PyoSynth
    # map = get_sfz_map_from_config('../config/dskconfig.json')
    # INST_PROGRAMS = {i: instrument_generator(4, sfz_voice_generator(name)) for i, name in enumerate(map.keys())}
    # PyoSynth.configure(INST_PROGRAMS, lambda *args: SFZVoice.read_sounds(map))
    # PyoSynth.configure_instrument_map(read_sfz_config('../config/dskconfig.json'))
    # main(PyoSynth(True))

    from music21_addons.sequencer import PyFluidSynth

    PyFluidSynth.init_synth('/Users/shiva/sounds/soundfonts/FluidR3_GM.sf2')
    PyFluidSynth.configure_instrument_map(get_flat_gm_instrument_map())
    main_window(PyFluidSynth())
