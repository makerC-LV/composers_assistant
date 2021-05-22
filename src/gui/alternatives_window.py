from tkinter import Toplevel, Listbox, BOTTOM, END, TOP, NW, X, N
from typing import List

from app_models.tracks import MultiTrack
from gui.main_window import AudioPlayerFrame, MultiTrackFrame


class AlternativesExplorer(Toplevel):

    def __init__(self, parent, title, alternatives):
        self.alternatives = alternatives
        Toplevel.__init__(self, parent)
        self.title = title

        self.player = AudioPlayerFrame(self)
        self.player.pack(side=TOP, anchor=NW, fill=X)
        self.multitrack_frame = MultiTrackFrame(self)
        self.multitrack_frame.pack(side=TOP, anchor=N, expand=True, fill='both')

        self.lbox = Listbox(self, width=45, height=25)
        self.lbox.pack(side=BOTTOM, expand=True, fill='both')
        self.lbox.bind('<Double-1>', self.select)
        self.fill_listbox(self.alternatives)

    def select(self, *args):
        sel = self.lbox.curselection()
        alt = self.lbox.get(sel)
        if alt is not None:
            self.multitrack.tracks[0].tiny.value = alt

    def fill_listbox(self, items: List[str]):
        self.lbox.delete(0, END)
        for item in items:
            self.lbox.insert(END, item)

    def connect(self, multi_track: MultiTrack):
        self.multitrack = multi_track
        self.player.connect(multi_track.player, multi_track.play, multi_track.stop)
        self.multitrack_frame.connect(self.multitrack)


def open_alternatives_explorer(root, synth, key, timesig, alternatives):
    ae = AlternativesExplorer(root, "Alternatives", alternatives)
    mt = MultiTrack(synth, key, timesig)
    mt.add_track()
    ae.connect(mt)
