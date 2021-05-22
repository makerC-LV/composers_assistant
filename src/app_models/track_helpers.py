import copy
from typing import Optional, List, Callable

from music21 import note, stream


def get_silence_of_duration(ncr: note.GeneralNote) -> Optional[note.Rest]:
    return note.Rest(duration=ncr.duration)


def replace_sel_with_silence(part: stream.Part, selected_items: List[note.GeneralNote]) -> stream.Part:
    for item in selected_items:
        repl = get_silence_of_duration(item)
        if repl is not None:
            part.replace(item, repl)
    return part


def transpose_fn(semitones: int) -> Callable:
    def inner(part):
        return part.transpose(semitones)

    return inner


def create_copy_track(part: stream.Part) -> stream.Part:
    return copy.deepcopy(part)


def create_drum_track(part: stream.Part) -> stream.Part:
    pass


def create_bass_track(part: stream.Part) -> stream.Part:
    pass


def create_chord_track(part: stream.Part) -> stream.Part:
    pass


def get_variations(part, selected_items):
    pass


def get_embellishments(part, selected_items):
    pass
