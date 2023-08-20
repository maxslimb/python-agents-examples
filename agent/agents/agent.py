import livekit
from typing import TypedDict
from typing_extensions import Unpack

class Agent:
    def __init__(self, *args, participant: livekit.LocalParticipant, room: livekit.Room):
        self.participant = participant
        self.room = room
        self.room.on("participant_connected", self._on_participant_connected_or_disconnected)
        self.room.on("participant_disconnected", self._on_participant_connected_or_disconnected)
        self.participants = self.room.participants

        self.initialize()

    async def cleanup(self):
        await self.room.disconnect()

    def initialize(self):
        raise NotImplementedError

    def on_video_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.VideoFrame):
        raise NotImplementedError
    
    def on_audio_frame(self, track: livekit.Track, participant: livekit.Participant, frame: livekit.AudioFrame):
        raise NotImplementedError

    def should_process(self, track: livekit.Track, participant: livekit.Participant) -> bool:
        raise NotImplementedError

    def on_participants_changed(self, participants: [livekit.Participant]):
        pass

    def _on_participant_connected_or_disconnected(self, *args):
        self.participants = self.room.participants
        self.on_participants_changed(self.participants)

    

    def has_non_agent_participants(self) -> bool:
        for participant in self.room.participants:
            if participant != self.participant:
                return True
        return False