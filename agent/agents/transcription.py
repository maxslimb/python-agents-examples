import livekit
from lib.whisper import Whisper
from agents.agent import Agent


class Transcription(Agent):
    def initialize(self):
        self.whisper = Whisper()

    def on_audio_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.AudioFrame):
        print("on_audio_frame")

    def on_video_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.VideoFrame):
        print("on_video_frame")

    def should_process(self, track: livekit.TrackPublication, participant: livekit.Participant) -> bool:
        print("should process", participant.identity)
        return track.kind == livekit.TrackKind.AUDIO
