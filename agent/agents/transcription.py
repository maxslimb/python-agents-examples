import livekit
from lib.whisper import Whisper
from agents.agent import Agent


class Transcription(Agent):
    def initialize(self):
        self.whisper = Whisper()

    def on_audio_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.AudioFrame):
        self.whisper.process_audio_frame(frame)

    def on_video_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.VideoFrame):
        raise NotImplementedError