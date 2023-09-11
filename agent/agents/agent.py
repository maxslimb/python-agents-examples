import asyncio
import livekit
from collections.abc import Callable, Awaitable

Should_Process_CB = Callable[[livekit.TrackPublication, livekit.Participant], Awaitable[bool]]

class Agent:
    def __init__(self, *_, participant: livekit.LocalParticipant, room: livekit.Room):
        self.participant = participant
        self.room = room
        self.room.on("participant_connected", self._on_participant_connected_or_disconnected)
        self.room.on("participant_disconnected", self._on_participant_connected_or_disconnected)
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("track_unsubscribed", self._on_track_unsubscribed)
        self.room.on("track_published", self._on_track_published)
        self.room.on("data_received", self._on_data_received)
        self.participants = self.room.participants
        self.should_process_cb = None

        self._handle_existing_tracks()
        self.audio_streams = []
        self.video_streams = []
        self.stream_tasks = set()

    async def cleanup(self):
        await self.room.disconnect()

    def _handle_existing_tracks(self):
        for participantKey in self.participants:
            for publicationKey in self.participants[participantKey].tracks:
                publication = self.participants[participantKey].tracks[publicationKey]
                self._on_track_published(publication, self.participants[participantKey])

    def _on_video_stream(self, stream: livekit.VideoStream, participant: livekit.Participant, track: livekit.Track):
        self.video_streams.append(stream)
        task = asyncio.get_event_loop().create_task(self.on_video_stream(stream, participant, track))
        asyncio.get_event_loop().call_soon_threadsafe(task)

    def _on_audio_stream(self, stream: livekit.AudioStream, participant: livekit.Participant, track: livekit.Track):
        self.audio_streams.append(stream)
        task = asyncio.create_task(self.on_audio_stream(stream, participant, track))
        self.stream_tasks.add(task)
        task.add_done_callback(self.stream_tasks.discard)

    async def on_video_stream(self, stream: livekit.VideoStream, participant: livekit.Participant, track: livekit.Track):
        pass

    async def on_audio_stream(self, stream: livekit.AudioStream, participant: livekit.Participant, track: livekit.Track):
        pass

    def should_process(self, track: livekit.TrackPublication, participant: livekit.Participant) -> bool:
        pass

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
        if publication.kind == 1:
            audio_stream = livekit.AudioStream(track)
            self._on_audio_stream(audio_stream, participant, track)
        elif publication.kind == 2:
            video_stream = livekit.VideoStream(track)
            self._on_video_stream(video_stream, participant, track)

    def _on_track_unsubscribed(self, publication: livekit.RemoteTrackPublication, participant: livekit.RemoteParticipant):
        self.audio_streams = [stream for stream in self.audio_streams if stream.track.sid != publication.track_sid]
        self.video_streams = [stream for stream in self.video_streams if stream.track.sid != publication.track_sid]

    def _on_data_received(self, data: bytearray, kind, participant: livekit.RemoteParticipant):
        print(data, self.participant.identity)