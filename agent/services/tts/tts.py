import os
import livekit
import threading
import asyncio
import queue
import numpy as np
import requests
import uuid
import audioread
from elevenlabs import generate, set_api_key, voices

CHUNK_SIZE = 1024


class TTS:
    def __init__(self, audio_source: livekit.AudioSource, sample_rate: int, num_channels: int):
        self._audio_source = audio_source
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._generated = False
        set_api_key(os.environ["ELEVENLABS_API_KEY"])

    async def generate_audio(self, text: str):
        t = threading.Thread(target=self._generate_audio_thread, args=(text,), daemon=True)
        t.start()

    def _generate_audio_http_thread(self, text: str):
        loop = asyncio.new_event_loop()
        t = loop.create_task(self._generate_audio_thread_http_async(text))
        loop.run_until_complete(t)

    async def _generate_audio_thread_async(self, text: str):
        audio = generate(text, voice=voices()[0], latency=3)

        # make dir if not exists
        os.makedirs("/tmp/kitt", exist_ok=True)

        filename = f"/tmp/kitt/{uuid.uuid4()}.mp3"

        # save to mp3
        with open(filename, "wb") as f:
            f.write(audio)

        with audioread.audio_open(filename) as f:
            print(f.channels, f.samplerate, f.duration)
            frame_size = int(f.samplerate / 100)
            for buf in f:
                buf_arr = np.frombuffer(buf, dtype=np.int16)
                for i in range(0, buf_arr.shape[0] - frame_size, frame_size):
                    frame = livekit.AudioFrame.create(sample_rate=f.samplerate, num_channels=f.channels, samples_per_channel=frame_size)
                    audio_data = np.ctypeslib.as_array(frame.data)
                    np.copyto(audio_data, buf_arr[i:i + frame_size])
                    resampled = frame.remix_and_resample(self._sample_rate, self._num_channels)
                    await self._audio_source.capture_frame(resampled)

        # delete file
        if os.path.exists(filename):
            os.remove(filename)

    # TODO: This is the http version that supports PCM and streaming,
    # but we don't have the right account to use it yet
    async def _generate_audio_thread_http_async(self, text: str):
        body = self._create_elevenlabs_body(text)
        headers = self._create_elevenlabs_header()
        voices_url = "https://api.elevenlabs.io/v1/voices"

        response = requests.get(voices_url, headers=headers, timeout=30)
        voice = response.json().get('voices', [])[0]
        voice_id = voice['voice_id']
        stream_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=pcm_44100"
        response = requests.post(stream_url, json=body, headers=headers, stream=True, timeout=30)
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            print("Got chunk: ", chunk)
            if chunk:
                frame = livekit.AudioFrame.create(sample_rate=48000, num_channels=1, samples_per_channel=480)
                audio_data = np.ctypeslib.as_array(frame.data)
                np.copyto(audio_data, chunk)

    def _create_elevenlabs_header(self):
        return {"Accept": "audio/x-wav;codec=pcm;rate=44100", "Content-Type": "application/json", "xi-api-key": os.environ["ELEVENLABS_API_KEY"]}

    def _create_elevenlabs_body(self, text: str):
        return {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
