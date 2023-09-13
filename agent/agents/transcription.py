import asyncio
import livekit
import numpy as np
from lib.whisper.whisper import Whisper
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

        whisper = Whisper()
        asyncio.create_task(self.print_whisper_results(whisper))
        async for frame in stream:
            resampled = frame.remix_and_resample(WHISPER_SAMPLE_RATE, 1)
            data = np.array(resampled.data, dtype=np.float32) / 32768.0
            whisper.add_buffer(data)

    async def print_whisper_results(self, whisper: Whisper):
        async for event in whisper:
            print(f"transcription event: {event.type} - text: {event.text} - seconds: {event.time_seconds}")

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
