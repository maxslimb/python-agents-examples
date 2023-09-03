import livekit
from whispercpp import Whisper
import numpy as np
import samplerate
from agents.agent import Agent


SECONDS_PER_WHISPER_INFERENCE = 3


class Transcription(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whisper = Whisper.from_pretrained("tiny.en")
        self.track_sid_sample_rates: {str: float} = {}
        self.track_sid_buffers: {str: np.ndarray} = {}
        self.track_sid_written_samples: {str: int} = {}

    def on_audio_frame(
        self,
        track: livekit.Track,
        participant: livekit.Participant,
        frame: livekit.AudioFrame,
    ):

        if participant.identity != "caller":
            return

        if track.sid not in self.track_sid_sample_rates:
            self.track_sid_sample_rates[track.sid] = frame.sample_rate

        if track.sid not in self.track_sid_written_samples:
            self.track_sid_written_samples[track.sid] = 0

        if self.track_sid_sample_rates[track.sid] != frame.sample_rate:
            print(
                "sample rate mismatch",
                self.track_sid_sample_rates[track.sid],
                frame.sample_rate,
            )
            return

        if track.sid not in self.track_sid_buffers:
            print("creating buffer for", track.sid, self.track_sid_sample_rates[track.sid])
            self.track_sid_buffers[track.sid] = np.zeros(
                SECONDS_PER_WHISPER_INFERENCE * self.track_sid_sample_rates[track.sid],
                dtype=np.float32,
            )

        data = np.array(frame.data, dtype=np.float32) / 32768.0
        data_start = self.track_sid_written_samples[track.sid]
        sample_limit = SECONDS_PER_WHISPER_INFERENCE * self.track_sid_sample_rates[track.sid]

        print("writing", data_start, len(data), sample_limit)

        self.track_sid_buffers[track.sid][data_start: data_start + len(data)] = data
        self.track_sid_written_samples[track.sid] += len(data)
        if self.track_sid_written_samples[track.sid] >= sample_limit:
            self.track_sid_written_samples[track.sid] = 0
            y = samplerate.resample(self.track_sid_buffers[track.sid], 16000 / self.track_sid_sample_rates[track.sid], "sinc_best")
            res = self.whisper.transcribe(y)
            print(res)

    def should_process(
        self, track: livekit.TrackPublication, participant: livekit.Participant
    ) -> bool:
        print("should process", participant.identity)
        return track.kind == 1
