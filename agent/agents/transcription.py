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

        print("NEIL gh 0 -----------------------------------------")
        written_samples = 0
        buffer = np.zeros(WHISPER_SAMPLE_RATE * SECONDS_PER_WHISPER_INFERENCE, dtype=np.float32)
        async for frame_coro in stream:
            frame = await frame_coro
            resampled = frame.remix_and_resample(WHISPER_SAMPLE_RATE, 1)
            data = np.array(resampled.data, dtype=np.float32) / 32768.0
            buffer[written_samples: written_samples + len(data)] = data
            written_samples += len(data)

            print("NEIL gh")

            if written_samples >= WHISPER_SAMPLE_RATE * SECONDS_PER_WHISPER_INFERENCE:
                print("NEIL gh 2")
                audio = whisper.pad_or_trim(buffer)
                mel = whisper.log_mel_spectrogram(audio, WHISPER_SAMPLE_RATE)
                options = whisper.DecodingOptions()
                result = whisper.decode(self.model, mel, options)
                written_samples = 0
                print(result.text)

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        return track.kind == 1
