import threading
from tkinter import Variable, Frame, PhotoImage, Button, IntVar, Scale, LEFT, W, X, StringVar, NW, RIGHT, TOP, \
    BooleanVar, Checkbutton, TclError, Widget, Menu, N, Tk, HORIZONTAL, Label
from tkinter.ttk import Spinbox
from typing import Callable, Dict

from composition.application import MultiTrack, AudioPlayer, Observable, Track, APSTATE_STOPPED, APSTATE_PLAYING, \
    APSTATE_PAUSED
from gui.search_combobox import Combobox_Autocomplete
from gui.text_with_var import TextWithVar
from gui.vertically_scrollable_frame import VerticalScrolledFrame

import logging

from utils.midi_instrument_defs import get_flat_gm_instrument_map

logger = logging.getLogger(__name__)


def connect_tvar_obs(tvar: Variable, obs: Observable, debug=False):
    def cb(var, indx, mode):
        obs.value = tvar.get()

    tvar.trace_add('write', cb)

    @obs.changed.register
    def obs_changed(old_value, new_value):
        if tvar.get() != new_value:
            tvar.set(new_value)
            if debug:
                logger.info("Setting tvar to (thread: %s) %s", threading.get_ident(), new_value)


class AudioPlayerFrame(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, highlightbackground="red", highlightthickness=1)
        self.play_icon = PhotoImage(file='../gui/play.png')
        self.pause_icon = PhotoImage(file='../gui/pause.png')
        self.stop_icon = PhotoImage(file='../gui/stop.png')
        self.playbutton = Button(self, image=self.play_icon)
        self.stopbutton = Button(self, image=self.stop_icon)
        self.cue_pos = IntVar()
        self.cue = Scale(self, from_=0, to=200, tickinterval=50, variable=self.cue_pos, orient=HORIZONTAL)
        self.tempo_label = Label(self, text="Tempo")
        self.tempo_value = IntVar()
        self.tempo_value.set(60)
        self.tempo = Spinbox(self, from_=0, to=240, textvariable=self.tempo_value, width=3)

        self.playbutton.pack(side=LEFT, anchor=W)
        self.stopbutton.pack(side=LEFT)
        self.cue.pack(side=LEFT, expand=True, fill=X)
        self.tempo_label.pack(side=LEFT)
        self.tempo.pack(side=LEFT)

    def connect(self, audio_player: AudioPlayer, play_fn: Callable, stop_fn: Callable):
        self.player = audio_player
        self.playbutton.configure(command=play_fn)
        self.stopbutton.configure(command=stop_fn)

        connect_tvar_obs(self.cue_pos, audio_player.cue_pos)
        connect_tvar_obs(self.tempo_value, audio_player.tempo)

        @audio_player.state.changed.register
        def state_changed(old_value, new_value):
            icon = None
            if new_value == APSTATE_STOPPED or new_value == APSTATE_PAUSED:
                icon = self.play_icon
            elif new_value == APSTATE_PLAYING:
                icon = self.pause_icon

            self.playbutton.configure(image=icon)

        @audio_player.length.changed.register
        def length_changed(old_value, new_value):
            len = new_value
            self.cue.configure(to=len, tickinterval=int(len / 4))


class InstrumentChooserCombobox(Combobox_Autocomplete):
    def __init__(self, parent, list_of_items):
        self.tvar = StringVar()
        Combobox_Autocomplete.__init__(
            self, parent,
            list_of_items=list_of_items,
            textvariable=self.tvar, ignorecase_match=False, startswith_match=False)

    def connect(self, obs: Observable):
        def cb(var, indx, mode):
            obs.value = self.tvar.get()

        self.tvar.trace_add('write', cb)

        @obs.changed.register
        def change_selection(old_value, new_value):
            if self.get_value() != new_value:
                self.set_value(new_value)


class TrackFrame(Frame):
    def __init__(self, parent, list_of_instruments):
        Frame.__init__(self, parent)
        self.left_frame = Frame(self)
        self.left_frame.pack(side=LEFT, anchor=NW, fill='y')
        self.right_frame = Frame(self)
        self.right_frame.pack(side=RIGHT, expand=True, fill='both')
        self.tnvar = StringVar()
        self.tn_entry = TextWithVar(self.right_frame, textvariable=self.tnvar, undo=True,
                                    autoseparators=True, maxundo=-1)
        self.tn_entry.pack(side=TOP, anchor=NW, expand=True, fill='x')
        self.tn_entry.bind("<Button-2>", self.do_popup)
        self.instchooser = InstrumentChooserCombobox(self.left_frame, list_of_instruments)
        self.instchooser.pack(side=TOP, anchor=NW)
        self.mutevar = BooleanVar()
        mute = Checkbutton(self.left_frame, text="Mute", variable=self.mutevar)
        mute.pack(side=TOP, anchor=W)
        self.solovar = BooleanVar()
        solo = Checkbutton(self.left_frame, text="Solo", variable=self.solovar)
        solo.pack(side=TOP, anchor=W)

    def connect(self, track: Track):
        self.track = track
        self.instchooser.connect(track.instrument)
        connect_tvar_obs(self.tnvar, track.tiny)
        connect_tvar_obs(self.mutevar, track.muted)
        connect_tvar_obs(self.solovar, track.soloed)

        @track.on_item.changed.register
        def playing_item_changed(old_val, new_val):
            # elogger.info("playing item", new_val)
            self.tn_entry.tag_delete("playing")
            if new_val is not None:
                sl, sc, el, ec = new_val
                start = f'{sl}.{sc - 1}'
                end = f'{el}.{ec - 1}'
                self.tn_entry.tag_add("playing", start, end)
                self.tn_entry.tag_config("playing", background="yellow", foreground="black")

    def do_popup(self, event):
        try:
            _ = self.tn_entry.selection_get()
        except TclError:
            _ = None
        menu = self.build_menu(self.track.menu, self.tn_entry)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def build_menu(self, menu_map: Dict, root: Widget):
        m = Menu(root, tearoff=0)
        for key, value in menu_map.items():
            if isinstance(value, dict):
                sm = self.build_menu(value, m)
                m.add_cascade(label=key, menu=sm, underline=0)
                if key == 'selection' and len(self.tn_entry.tag_ranges("sel")) == 0:
                    m.entryconfig(key, state="disabled")
            else:
                m.add_command(label=key, command=value)
        return m


class MultiTrackFrame(VerticalScrolledFrame):
    def __init__(self, parent):
        VerticalScrolledFrame.__init__(self, parent)
        self.configure(highlightbackground="blue", highlightthickness=1)
        self.tracks = []

    def add_track(self):
        self.multitrack.add_track()

    def track_added(self, multi_track, new_track):
        self.connect(multi_track)

    def connect(self, multi_track: MultiTrack):
        self.multitrack = multi_track
        my_tracks = [track for track, trackframe in self.tracks]
        for track in multi_track.tracks:
            if track not in my_tracks:
                frame = TrackFrame(self.interior, track.get_instrument_names())
                frame.connect(track)
                frame.pack(side=TOP, anchor=W, expand=True, fill='x')
                self.tracks.append((track, frame))


class MainWindow(Frame):

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.configure(background='#BcBcBc')
        self.player = AudioPlayerFrame(self)
        self.player.pack(side=TOP, anchor=NW, fill=X)
        self.multitrack_frame = MultiTrackFrame(self)
        self.multitrack_frame.pack(side=TOP, anchor=N, expand=True, fill='both')

        self.master.title("Compose!")

        menubar = Menu(self.master)
        self.master.config(menu=menubar)

        trackmenu = Menu(menubar)
        menubar.add_cascade(label="Track", menu=trackmenu)
        trackmenu.add_command(label="Add track", command=self.add_track)

    def add_track(self):
        self.multitrack.add_track()

    def track_added(self, multi_track, new_track):
        self.connect(multi_track)

    def connect(self, multi_track: MultiTrack):
        self.multitrack = multi_track
        self.player.connect(multi_track.player, multi_track.play, multi_track.stop)
        self.multitrack_frame.connect(self.multitrack)


def main(synth):
    root = Tk()
    mw = MainWindow(root)
    mt = MultiTrack(mw, synth)
    mw.connect(mt)
    mw.pack(expand=True, fill='both', padx=2, pady=2)
    mw.mainloop()


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
    main(PyFluidSynth())
