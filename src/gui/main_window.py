import logging
import threading
from tkinter import Variable, Frame, PhotoImage, Button, IntVar, Scale, LEFT, W, X, StringVar, NW, RIGHT, TOP, \
    BooleanVar, Checkbutton, TclError, Widget, Menu, N, Tk, HORIZONTAL, Label, simpledialog
from tkinter.ttk import Spinbox
from typing import Callable, Dict

from app_models.audio_player import AudioPlayer, APSTATE_STOPPED, APSTATE_PAUSED, APSTATE_PLAYING
from app_models.event_observable import Observable
from app_models.main_model import MainWindowTrack, MainWindowMultiTrack
from gui.search_listbox import SearchListbox
from gui.text_with_var import TextWithVar
from gui.vertically_scrollable_frame import VerticalScrolledFrame

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


class InstrumentChooserButton(Button):
    def __init__(self, parent, list_of_items):
        self.tvar = StringVar()
        self.list_of_items = list_of_items
        Button.__init__(
            self, parent,
            textvariable=self.tvar, command=self.show_instruments)

    def connect(self, obs: Observable):
        def cb(var, indx, mode):
            obs.value = self.tvar.get()

        self.tvar.trace_add('write', cb)

        @obs.changed.register
        def change_selection(old_value, new_value):
            if self.tvar.get() != new_value:
                self.tvar.set(new_value)

    def show_instruments(self):
        dialog = InstrumentChooserDialog(title="Select instrument", parent=self, items=self.list_of_items)
        if dialog.selected is not None and self.tvar.get() != dialog.selected:
            self.tvar.set(dialog.selected)


class InstrumentChooserDialog(simpledialog.Dialog):
    def __init__(self, parent, title, items):
        self.selected = None
        self.items = items
        super().__init__(parent, title)

    def body(self, frame):
        self.my_slistbox = SearchListbox(frame, self.items)
        self.my_slistbox.pack(side=TOP, expand=True, fill='both')

        return frame

    def ok_pressed(self):
        logger.info("ok")
        self.selected = self.my_slistbox.get_selection()
        self.destroy()

    def cancel_pressed(self):
        logger.info("cancel")
        self.selected = None
        self.destroy()

    def buttonbox(self):
        self.ok_button = Button(self, text='OK', width=5, command=self.ok_pressed)
        self.ok_button.pack(side="left")
        cancel_button = Button(self, text='Cancel', width=5, command=self.cancel_pressed)
        cancel_button.pack(side="right")
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())


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
        self.instchooser = InstrumentChooserButton(self.left_frame, list_of_instruments)
        self.instchooser.pack(side=TOP, anchor=NW)
        self.mutevar = BooleanVar()
        mute = Checkbutton(self.left_frame, text="Mute", variable=self.mutevar)
        mute.pack(side=TOP, anchor=W)
        self.solovar = BooleanVar()
        solo = Checkbutton(self.left_frame, text="Solo", variable=self.solovar)
        solo.pack(side=TOP, anchor=W)

    def connect(self, track: MainWindowTrack):
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

    def build_menu(self, menu_map: Dict, root: Widget, needs_sel=False):
        m = Menu(root, tearoff=0)
        for key, cmd in menu_map.items():
            if isinstance(cmd, dict):
                needs_sel = key == 'selection'
                sm = self.build_menu(cmd, m, needs_sel)
                m.add_cascade(label=key, menu=sm, underline=0)
                if key == 'selection' and len(self.tn_entry.tag_ranges("sel")) == 0:
                    m.entryconfig(key, state="disabled")

            else:
                if needs_sel:
                    m.add_command(label=key, command=self.invoke_with_sel(cmd))
                else:
                    m.add_command(label=key, command=cmd)
        return m

    def invoke_with_sel(self, func):
        def f():
            sel = self.tn_entry.tag_ranges("sel")
            [sl, sc, el, ec] = [int(x) for x in str(sel[0]).split('.') + str(sel[1]).split('.')]
            func(sl, sc, el, ec)

        return f


class MultiTrackFrame(VerticalScrolledFrame):
    def __init__(self, parent):
        VerticalScrolledFrame.__init__(self, parent)
        self.configure(highlightbackground="blue", highlightthickness=1)
        self.tracks = []

    def add_track(self):
        self.multitrack.add_track()

    def track_added(self, multi_track, new_track):
        self.connect(multi_track)

    def connect(self, multi_track: MainWindowMultiTrack):
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

    def connect(self, multi_track: MainWindowMultiTrack):
        self.multitrack = multi_track
        self.player.connect(multi_track.player, multi_track.play, multi_track.stop)
        self.multitrack_frame.connect(self.multitrack)

    def open_alternatives(self, alternatives):
        from gui.alternatives_window import open_alternatives_explorer
        open_alternatives_explorer(self, self.multitrack.player.sequencer.synth, self.multitrack.key,
                                   self.multitrack.timesig, alternatives)


def main_window(synth):
    root = Tk()
    mw = MainWindow(root)
    mt = MainWindowMultiTrack(mw, synth)
    mw.connect(mt)
    mw.pack(expand=True, fill='both', padx=2, pady=2)
    mw.mainloop()
