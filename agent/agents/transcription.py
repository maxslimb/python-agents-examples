import asyncio
import livekit
import numpy as np
from services.transcription import Transcriber
from agents.agent import Agent


WHISPER_SAMPLE_RATE = 16000


class Transcription(Agent):

    async def on_audio_stream(
        self,
        stream: livekit.AudioStream,
        participant: livekit.Participant,
        track: livekit.Track,
    ):
        if participant.identity != "caller":
            return

        transcriber = Transcriber()
        asyncio.create_task(self._print_whisper_results(transcriber))
        async for frame in stream:
            resampled = frame.remix_and_resample(WHISPER_SAMPLE_RATE, 1)
            data = np.array(resampled.data, dtype=np.float32) / 32768.0
            transcriber.add_buffer(data)

    async def _print_whisper_results(self, transcriber: Transcriber):
        async for event in transcriber:
            print(f"transcription event: {event.type} - text: {event.text} - seconds: {event.time_seconds}")

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
