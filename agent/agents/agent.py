import livekit

class Agent:
    def __init__(self, participant: livekit.LocalParticipant):
        self.participant = participant
        self.initialize()

    def initialize(self):
        raise NotImplementedError

    def on_video_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.VideoFrame):
        raise NotImplementedError
    
    def on_audio_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.AudioFrame):
        raise NotImplementedError

    def should_process(self, track: livekit.Track, participant: livekit.Participant) -> bool:
        raise NotImplementedError