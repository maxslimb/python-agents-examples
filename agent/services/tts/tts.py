import asyncio
import os
import livekit
import numpy as np
import websockets.client as wsclient
import websockets.exceptions
import aiohttp
import json
import base64

class TTS:
    def __init__(self, audio_source: livekit.AudioSource, sample_rate: int, num_channels: int):
        self._audio_source = audio_source
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._voice_id = ""
        self._ws: wsclient.WebSocketClientProtocol = None

    async def warmup(self):
        print("NEIL warming up")
        if self._ws is not None and self._ws.open:
            print("Already connected from a previous session, killing it")
            await self._ws.close()
            self._ws = None

        await self._get_voice_id_if_needed()
        asyncio.create_task(self._receive_audio_loop())
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}/stream-input?model_id=eleven_monolingual_v1&output_format=pcm_44100&optimize_streaming_latency=2"
        self._ws = await wsclient.connect(uri)
        bos_message = {"text": " ", "xi_api_key": os.environ["ELEVENLABS_API_KEY"]}
        await self._ws.send(json.dumps(bos_message))

    async def generate_audio(self, text: str):
        text_queue = asyncio.Queue()
        await text_queue.put(text)
        await text_queue.put(None)
        await self.stream_generate_audio(text_queue=text_queue)

    async def stream_generate_audio(self, text_queue: asyncio.Queue[str]):
        await self._get_voice_id_if_needed()
        while self._ws is None or self._ws.open is False:
            print("Waiting for ws")
            await asyncio.sleep(0.1)

        while True:
            text = await text_queue.get()
            if text is None:
                await self._ws.send(json.dumps({"text": ""}))
                return

            payload = {"text": f"{text} ", "try_trigger_generation": True}
            await self._ws.send(json.dumps(payload))

    async def _receive_audio_loop(self):
        while self._ws is None or self._ws.open is False:
            await asyncio.sleep(0.1)

        try:
            remainder = b''
            while True:
                response = await self._ws.recv()
                data = json.loads(response)

                if data['isFinal']:
                    print("Is Final Closing the Websocket")
                    await self._ws.close()
                    return

                if data["audio"]:
                    chunk = remainder + base64.b64decode(data["audio"])

                    # pad chunk to fit 441 sample frames
                    if len(chunk) < 441 * 2:
                        chunk = chunk + b'\x00' * (441 * 2 - len(chunk))
                    else:
                        remainder = chunk[-(len(chunk) % (441 * 2)):]

                    buf_arr = np.frombuffer(chunk, dtype=np.int16)

                    for i in range(0, buf_arr.shape[0] - 441, 441):
                        frame = livekit.AudioFrame.create(sample_rate=self._sample_rate, num_channels=1, samples_per_channel=441)
                        audio_data = np.ctypeslib.as_array(frame.data)
                        np.copyto(audio_data, buf_arr[i: i + 441])
                        resampled = frame.remix_and_resample(self._sample_rate, self._num_channels)
                        await self._audio_source.capture_frame(resampled)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            return

    async def _get_voice_id_if_needed(self):
        if self._voice_id == "":
            voices_url = "https://api.elevenlabs.io/v1/voices"
            async with aiohttp.ClientSession() as session:
                async with session.get(voices_url) as resp:
                    json_resp = await resp.json()
                    voice = json_resp.get('voices', [])[0]
                    self._voice_id = voice['voice_id']
