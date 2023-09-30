import asyncio
from collections.abc import Callable
import logging
import threading
from dataclasses import dataclass

import whisper
import livekit
import numpy as np


model = whisper.load_model('tiny.en')

WHISPER_SAMPLE_RATE = 16000
STEP_SIZE_SECONDS = 1
MAX_TALKING_SECONDS = 30

EVENT_TYPE_TALKING_STARTED = "monologue_started"
EVENT_TYPE_TALKING_FINISHED = "monologue_finished"
EVENT_TYPE_TALKING_UPDATED = "monologue_updated"
EVENT_TYPE_NO_SPEECH = "no_speech"

class Transcriber:

    @dataclass
    class Event:
        id: str
        type: str
        text: str
        time_seconds: float

    def __init__(self, audio_track: livekit.RemoteAudioTrack, callback: Callable[[Event], None]):
        self._callback = callback
        self._audio_track = audio_track
        self._main_event_loop = asyncio.get_event_loop()
        self._write_index = 0
        self._in_monologue = False
        self._working_buffer = np.zeros(MAX_TALKING_SECONDS * WHISPER_SAMPLE_RATE, dtype=np.float32)
        self._delta_buffer_write_index = 0
        self._delta_buffer = np.zeros(WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS, dtype=np.float32)
        self._last_text = ""
        self._current_id = 1
        self._silence_buffer_count = 0

    def start(self):
        threading.Thread(target=self._create_stream, daemon=True).start()

    def _create_stream(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stream = livekit.AudioStream(self._audio_track, loop)
        loop.run_until_complete(self._process_loop(stream))

    async def _process_loop(self, stream: livekit.AudioStream):
        async for frame in stream:
            resampled = frame.remix_and_resample(WHISPER_SAMPLE_RATE, 1)
            data = np.array(resampled.data, dtype=np.float32) / 32768.0
            self._add_buffer(data)

    def _add_buffer(self, buffer: np.array) -> None:
        buffer_size = len(buffer)

        if buffer_size + self._delta_buffer_write_index > WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS:
            logging.error("Received buffer larger than step size, truncating")
            buffer = buffer[0:WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS - self._delta_buffer_write_index]

        self._delta_buffer[self._delta_buffer_write_index:self._delta_buffer_write_index + buffer_size] = buffer
        self._delta_buffer_write_index += buffer_size

        # Normal case, we've recieved enough buffers to fill up the step size
        if self._delta_buffer_write_index >= WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS:
            self._delta_buffer_write_index = 0
            delta_res = self._transcribe(self._delta_buffer)

            if delta_res != "":
                # We've received enough buffers to fill up the max monologue size so we finish any
                # monologue we're in and start a new one. This can cause a monologue to be split or
                # glitched if the speaker is speaking for longer than the max monologue size. Consider
                # a better solution using some sort of sliding window design.
                if self._write_index >= len(self._working_buffer):
                    self._last_text = self._transcribe(self._working_buffer[0:self._write_index])
                    if self._in_monologue:
                        self._finish_talking()

                self._working_buffer[self._write_index:self._write_index + len(self._delta_buffer)] = self._delta_buffer
                self._write_index += len(self._delta_buffer)
                self._last_text = self._transcribe(self._working_buffer[0:self._write_index])

                if self._in_monologue:
                    self._update_talking()
                else:
                    self._start_talking()
            else:
                self._silence_buffer_count += WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS
                if self._in_monologue:
                    self._finish_talking()
                    self._start_silence()
                else:
                    self._update_silence()

    def _start_talking(self):
        self._in_monologue = True
        self._silence_buffer_count = 0
        self._current_id += 1
        event = Transcriber.Event(id=self._current_id,
                                  text=self._last_text,
                                  type=EVENT_TYPE_TALKING_STARTED,
                                  time_seconds=self._write_index / WHISPER_SAMPLE_RATE)
        self._main_event_loop.call_soon_threadsafe(self._callback, event)

    def _update_talking(self):
        event = Transcriber.Event(id=self._current_id,
                                  text=self._last_text,
                                  type=EVENT_TYPE_TALKING_UPDATED,
                                  time_seconds=self._write_index / WHISPER_SAMPLE_RATE)
        self._main_event_loop.call_soon_threadsafe(self._callback, event)

    def _finish_talking(self):
        self._in_monologue = False
        event = Transcriber.Event(id=self._current_id,
                                  text=self._last_text,
                                  type=EVENT_TYPE_TALKING_FINISHED,
                                  time_seconds=self._write_index / WHISPER_SAMPLE_RATE)
        self._last_text = ""
        self._write_index = 0
        self._main_event_loop.call_soon_threadsafe(self._callback, event)

    def _start_silence(self):
        self._current_id += 1
        event = Transcriber.Event(id=self._current_id,
                                  text="",
                                  type=EVENT_TYPE_NO_SPEECH,
                                  time_seconds=self._silence_buffer_count / WHISPER_SAMPLE_RATE)
        self._main_event_loop.call_soon_threadsafe(self._callback, event)

    def _update_silence(self):
        event = Transcriber.Event(id=self._current_id,
                                  text="",
                                  type=EVENT_TYPE_NO_SPEECH,
                                  time_seconds=self._silence_buffer_count / WHISPER_SAMPLE_RATE)
        self._main_event_loop.call_soon_threadsafe(self._callback, event)

    def _transcribe(self, buffer: np.array) -> str:
        res = whisper.transcribe(model, buffer)

        #print(res)

        segments = res.get('segments', [])
        result = ""
        for segment in segments:
            if segment['no_speech_prob'] < 0.5:
                result += segment["text"]

        return result
