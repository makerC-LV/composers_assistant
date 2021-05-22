import threading
from io import StringIO

from music21 import stream, instrument

from music21_addons.onetrack import parse_onetrack, to_part
from music21_addons.sequencer import MySequencer, MidoSynth


def gen_now_playing(file=None):
    def now_playing_fn(pl=None):
        print("now playing:", pl, file=file)

    return now_playing_fn


def gen_pupdate(file=None):
    def pupdate(pos, length):
        print("pupdate:", pos, length, file=file)

    return pupdate


def gen_finished(event=None, file=None):
    def finished():
        print("Finished", file=file)
        if event is not None:
            event.set()

    return finished


tmt_result = \
"""now playing: [<music21.note.Note C->]
pupdate: 0 3000
now playing: [<music21.note.Note A>]
pupdate: 500 3000
now playing: [<music21.note.Note A>]
pupdate: 1000 3000
now playing: [<music21.note.Note A>]
pupdate: 1500 3000
now playing: [<music21.chord.Chord A4 B4>]
pupdate: 2000 3000
now playing: [<music21.chord.Chord C4 D4 E4>]
pupdate: 2500 3000
now playing: []
pupdate: 3000 3000
Finished
"""    # noqa


def test_midi_transmission():
    """ If a DAW is connected to your midi bus, you should hear sound"""
    s = "C-6 Aq A:100 Aq:100 [a b4]q [c d e]q:100 v:60"
    p, map = to_part(parse_onetrack(s))
    p.insert(0, instrument.instrumentFromMidiProgram(0))
    score = stream.Score()
    score.insert(0, p)
    seq = MySequencer(MidoSynth())
    file = StringIO()
    play_over = threading.Event()
    seq.play(score, 120, now_playing=gen_now_playing(file), progress_update=gen_pupdate(file),
             finished_cb=gen_finished(play_over, file))
    play_over.wait()
    assert tmt_result == file.getvalue()
