from music21 import stream

from app_models.event_observable import Observable
from music21_addons.sequencer import Synth, MySequencer

APSTATE_PAUSED = 'Paused'
APSTATE_STOPPED = 'Stopped'
APSTATE_PLAYING = 'Playing'


class AudioPlayer():
    def __init__(self, synth: Synth):
        self.state = Observable(APSTATE_STOPPED)
        self.tempo = Observable(60)
        self.length = Observable(60000)
        self.cue_pos = Observable(0)
        self.sequencer = MySequencer(synth)

    def play_or_pause(self, tracks, timesig):
        if self.state.value == APSTATE_PLAYING:
            self.pause()
        elif self.state.value == APSTATE_PAUSED:
            self.unpause()
        elif self.state.value == APSTATE_STOPPED:
            self.play(tracks, timesig, self.tempo.value)

    def play(self, tracks, timesig, bpm):
        parts = []
        self.tracks = tracks
        solo_tracks = [t for t in tracks if t.soloed.value]
        solo_track = None if len(solo_tracks) == 0 else solo_tracks[0]
        for t in tracks:
            part = t.get_part()
            if t.muted.value or (solo_track and t != solo_track):
                part = (part[0].template(), {})  # Remove all notes and fill with rests, empty map
            parts.append(part)
        if len(parts) > 0:
            cmap = {}
            score = stream.Score()
            for p, map in parts:
                score.insert(0, p)
                cmap.update(map)

            def now_playing(playing_list):
                for obj in playing_list:
                    (lobj, ncr, track) = cmap[id(obj)]
                    track.now_playing(lobj)

            def progress_update(position, length):
                self.cue_pos.value = position
                self.length.value = length

            self.sequencer.play(score, bpm, now_playing, progress_update, self.finished)
            self.state.value = APSTATE_PLAYING

    def pause(self):
        if self.state.value == APSTATE_PLAYING:
            self.state.value = APSTATE_PAUSED
            self.sequencer.pause()

    def unpause(self):
        if self.state.value == APSTATE_PAUSED:
            self.state.value = APSTATE_PLAYING
            self.sequencer.unpause()

    def stop(self):
        self.sequencer.stop()
        self.state.value = APSTATE_STOPPED

    def finished(self, dummy=None):
        # print("Finished")
        self.cue_pos.value = 0
        self.state.value = APSTATE_STOPPED
        if self.tracks:
            for t in self.tracks:
                t.now_playing(None)
