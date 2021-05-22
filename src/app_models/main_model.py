import logging

from music21 import key, meter

from app_models.track_helpers import transpose_fn, create_copy_track, create_chord_track, create_bass_track, \
    create_drum_track, replace_sel_with_silence, get_variations, get_embellishments
from app_models.tracks import Track, MultiTrack
from music21_addons.onetrack import part_to_onetrack

logger = logging.getLogger(__name__)


class MainWindowTrack(Track):

    def __init__(self, multitrack, timesig, tkey, imap):
        super().__init__(multitrack, timesig, tkey, imap)
        self.menu = self.build_menu_map()

    def build_menu_map(self):
        m = {
            'aaa': self.aaa,
            'track': {
                'Transpose': {str(x): self.track_modifier_fn(transpose_fn(x)) for x in range(-12, 13)},
                'Create copy track': self.track_creator_fn(create_copy_track),
                'Create chord track': self.track_creator_fn(create_chord_track),
                'Create bass track': self.track_creator_fn(create_bass_track),
                'Create drum track': self.track_creator_fn(create_drum_track),

            },
            'selection': {
                'Replace selection with silence': self.sel_modifier_fn(replace_sel_with_silence),
                'Open variations window...': self.sel_variations_fn(get_variations),
                'Open embellishments window...': self.sel_variations_fn(get_embellishments),
            }
        }
        return m

    def track_modifier_fn(self, fn):
        def inner():
            p, m = self.get_part()
            new_part = fn(p)
            self.tiny.value = part_to_onetrack(new_part)

        return inner

    def track_creator_fn(self, fn):
        def inner():
            p, m = self.get_part()
            new_part = fn(p)
            new_track = self.multitrack.add_track()
            new_track.tiny.value = part_to_onetrack(new_part)

        return inner

    def sel_variations_fn(self, fn):
        def inner(sl, sc, el, ec):
            p, sel = self.get_selected_elements(sl, sc, el, ec)
            variations = fn(p, sel)
            alt_list = [part_to_onetrack(part) for part in variations]
            self.multitrack.gui.open_alternatives(alt_list)

        return inner

    def sel_modifier_fn(self, fn):
        def inner(sl, sc, el, ec):
            p, sel = self.get_selected_elements(sl, sc, el, ec)
            new_part = fn(p, sel)
            self.tiny.value = part_to_onetrack(new_part)

        return inner

    def get_selected_elements(self, sl, sc, el, ec):
        p, m = self.get_part()
        sel_items = []
        logger.debug("Incoming selection: %s, %s, %s, %s", sl, sc, el, ec)
        for lobj, ncr, _track in m.values():
            logger.debug("Object: %s  loc: %s", lobj, lobj.location())
            if lobj.location_intersects(sl, sc + 1, el, ec):
                sel_items.append(ncr)

        return p, sel_items

    def aaa(self):
        self.multitrack.gui.open_alternatives(['c d e', 'g a b'])


class MainWindowMultiTrack(MultiTrack):
    def __init__(self, gui, synth, key=key.Key('C'), timesig=meter.TimeSignature('4/4')):
        super().__init__(synth, key, timesig)
        self.gui = gui

    def add_track(self):
        new_track = MainWindowTrack(self, self.timesig, self.key,
                                    self.player.sequencer.synth.get_instrument_map())
        self.tracks.append(new_track)
        self.gui.track_added(self, new_track)
        new_track.instrument.value = new_track.get_instrument_names()[0]
        return new_track
