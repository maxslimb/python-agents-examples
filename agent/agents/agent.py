import livekit

class Agent:
    def __init__(self, *_, participant: livekit.LocalParticipant, room: livekit.Room):
        self.participant = participant
        self.room = room
        self.room.on("participant_connected",
                     self._on_participant_connected_or_disconnected)
        self.room.on("participant_disconnected",
                     self._on_participant_connected_or_disconnected)
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("track_unsubscribed", self._on_track_unsubscribed)
        self.room.on("track_published", self._on_track_published)
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

    def should_process(self, track: livekit.TrackPublication, participant: livekit.Participant) -> bool:
        raise NotImplementedError

    def on_participants_changed(self, participants: [livekit.Participant]):
        pass

    def _on_participant_connected_or_disconnected(self, *args):
        self.participants = self.room.participants
        self.on_participants_changed(self.participants)

    def _on_track_published(self, publication: livekit.RemoteTrackPublication, participant: livekit.Participant):
        # Don't do anything for our own tracks
        if participant.sid == self.participant.sid:
            return

        if self.should_process(publication, participant):
            publication.set_subscribed(True)

    def _on_track_subscribed(self, track: livekit.Track, publication: livekit.RemoteTrackPublication, participant: livekit.RemoteParticipant):
        if publication.kind == livekit.TrackKind.VIDEO:
            video_stream = livekit.VideoStream(track)
            video_stream.on("video_frame", lambda frame: self.on_video_frame(track, participant, frame))
        elif publication.kind == livekit.TrackKind.AUDIO:
            audio_stream = livekit.VideoStream(track)
            audio_stream.on("audio_frame", lambda frame: self.on_audio_frame(track, participant, frame))

    def _on_track_unsubscribed(self, publication: livekit.RemoteTrackPublication, participant: livekit.RemoteParticipant):
        pass

    def has_non_agent_participants(self) -> bool:
        for participant in self.room.participants:
            if participant != self.participant:
                return True
        return False
