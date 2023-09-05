import livekit
from whispercpp import Whisper
import numpy as np
from agents.agent import Agent
from agents.stream import AudioStream


SECONDS_PER_WHISPER_INFERENCE = 3
WHISPER_SAMPLE_RATE = 16000


class Transcription(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whisper = Whisper.from_pretrained("tiny.en")

    async def on_audio_stream(
        self,
        agent_stream: AudioStream,
        participant: livekit.Participant,
        track: livekit.Track,
    ):
        if participant.identity != "caller":
            return

        written_samples = 0
        buffer = np.zeros(WHISPER_SAMPLE_RATE * SECONDS_PER_WHISPER_INFERENCE, dtype=np.float32)
        async for frame_coro in agent_stream:
            frame = await frame_coro
            resampled = frame.remix_and_resample(WHISPER_SAMPLE_RATE, 1)
            data = np.array(resampled.data, dtype=np.float32) / 32768.0
            buffer[written_samples: written_samples + len(data)] = data
            written_samples += len(data)

            if written_samples >= WHISPER_SAMPLE_RATE * SECONDS_PER_WHISPER_INFERENCE:
                res = self.whisper.transcribe(buffer)
                written_samples = 0
                print(res)

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
