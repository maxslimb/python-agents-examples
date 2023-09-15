import livekit
from services.transcription import Transcriber
from agents.agent import Agent


class Transcription(Agent):

    def on_audio_track(
        self,
        track: livekit.Track,
        participant: livekit.Participant,
    ):
        if participant.identity != "caller":
            return

        transcriber = Transcriber(audio_track=track, callback=self._transcriber_cb)
        transcriber.start()

    def _transcriber_cb(self, event: Transcriber.Event):
        print(f"transcription event: {event.type} - text: {event.text} - seconds: {event.time_seconds}")

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
