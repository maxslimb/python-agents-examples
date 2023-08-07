import livekit
from lib.whisper import Whisper
from agents.agent import Agent


class Transcription(Agent):
    def __init__(self):
        self.whisper = Whisper()

    # TODO: Implement this, should only process on audio tracks
    def should_process(self, track: livekit.Track, participant: livekit.Participant) -> bool:
        return True

    def on_audio_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.AudioFrame):
        return super().on_audio_frame(track, participant, frame)