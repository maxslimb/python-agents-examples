import livekit
import numpy as np
import whisper
from agents.agent import Agent


SECONDS_PER_WHISPER_INFERENCE = 3
WHISPER_SAMPLE_RATE = 16000


class Transcription(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = whisper.load_model("tiny.en")

    async def on_audio_stream(
        self,
        stream: livekit.AudioStream,
        participant: livekit.Participant,
        track: livekit.Track,
    ):
        if participant.identity != "caller":
            return

        written_samples = 0
        buffer = np.zeros(WHISPER_SAMPLE_RATE * SECONDS_PER_WHISPER_INFERENCE, dtype=np.float32)
        async for frame in stream:
            resampled = frame.remix_and_resample(WHISPER_SAMPLE_RATE, 1)
            data = np.array(resampled.data, dtype=np.float32) / 32768.0
            buffer[written_samples: written_samples + len(data)] = data
            written_samples += len(data)

            if written_samples >= WHISPER_SAMPLE_RATE * SECONDS_PER_WHISPER_INFERENCE:
                res = whisper.transcribe(self.model, buffer)
                written_samples = 0

                segments = res.get('segments', [])
                for segment in segments:
                    if segment['no_speech_prob'] < 0.5:
                        print(segment)
                    else:
                        print("No speech detected")

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
