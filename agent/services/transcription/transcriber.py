import asyncio
import logging
from dataclasses import dataclass

import whisper
import numpy as np


model = whisper.load_model('tiny.en')

WHISPER_SAMPLE_RATE = 16000
STEP_SIZE_SECONDS = 1
MAX_MONOLOGUE_SECONDS = 30

EVENT_TYPE_MONOLOGUE_STARTED = "monologue_started"
EVENT_TYPE_MONOLOGUE_FINISHED = "monologue_finished"
EVENT_TYPE_MONOLOGUE_UPDATED = "monologue_updated"
EVENT_TYPE_NO_SPEECH = "no_speech"

class Transcriber:

    @dataclass
    class Event:
        id: str
        type: str
        text: str
        time_seconds: float

    def __init__(self):
        self._write_index = 0
        self._in_monologue = False
        self._working_buffer = np.zeros(MAX_MONOLOGUE_SECONDS * WHISPER_SAMPLE_RATE, dtype=np.float32)
        self._delta_buffer_write_index = 0
        self._delta_buffer = np.zeros(WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS, dtype=np.float32)
        self._last_text = ""
        self._current_id = 1
        self._silence_buffer_count = 0
        self._event_queue = asyncio.Queue[Transcriber.Event]()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self._event_queue.get()

    def add_buffer(self, buffer: np.array) -> None:
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
                        self._finish_monologue()
                    self._write_index = 0

                self._working_buffer[self._write_index:self._write_index + len(self._delta_buffer)] = self._delta_buffer
                self._write_index += len(self._delta_buffer)
                self._last_text = self._transcribe(self._working_buffer[0:self._write_index])

                if self._in_monologue:
                    self._update_monologue()
                else:
                    self._start_monologue()
            else:
                self._silence_buffer_count += WHISPER_SAMPLE_RATE * STEP_SIZE_SECONDS
                if self._in_monologue:
                    self._finish_monologue()
                    self._start_silence()
                else:
                    self._update_silence()

    def _start_monologue(self):
        self._in_monologue = True
        self._silence_buffer_count = 0
        self._current_id += 1
        self._event_queue.put_nowait(Transcriber.Event(id=self._current_id,
                                                       text=self._last_text,
                                                       type=EVENT_TYPE_MONOLOGUE_STARTED,
                                                       time_seconds=self._write_index / WHISPER_SAMPLE_RATE))

    def _update_monologue(self):
        self._event_queue.put_nowait(Transcriber.Event(id=self._current_id,
                                                       text=self._last_text,
                                                       type=EVENT_TYPE_MONOLOGUE_UPDATED,
                                                       time_seconds=self._write_index / WHISPER_SAMPLE_RATE))

    def _finish_monologue(self):
        self._in_monologue = False
        self._event_queue.put_nowait(Transcriber.Event(id=self._current_id,
                                                       text=self._last_text,
                                                       type=EVENT_TYPE_MONOLOGUE_FINISHED,
                                                       time_seconds=self._write_index / WHISPER_SAMPLE_RATE))
        self._last_text = ""

    def _start_silence(self):
        self._current_id += 1
        self._event_queue.put_nowait(Transcriber.Event(id=self._current_id,
                                                       text="",
                                                       type=EVENT_TYPE_NO_SPEECH,
                                                       time_seconds=self._silence_buffer_count / WHISPER_SAMPLE_RATE))

    def _update_silence(self):
        self._event_queue.put_nowait(Transcriber.Event(id=self._current_id,
                                                       text="",
                                                       type=EVENT_TYPE_NO_SPEECH,
                                                       time_seconds=self._silence_buffer_count / WHISPER_SAMPLE_RATE))

    def _transcribe(self, buffer: np.array) -> str:
        res = whisper.transcribe(model, buffer)

        segments = res.get('segments', [])
        result = ""
        for segment in segments:
            if segment['no_speech_prob'] < 0.5:
                result += segment["text"]

        return result
