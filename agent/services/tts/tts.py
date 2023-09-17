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
        self._generated = False
        self._voice_id = ""

    async def generate_audio(self, text: str):
        if self._voice_id == "":
            voices_url = "https://api.elevenlabs.io/v1/voices"
            async with aiohttp.ClientSession() as session:
                async with session.get(voices_url) as resp:
                    json_resp = await resp.json()
                    voice = json_resp.get('voices', [])[0]
                    self._voice_id = voice['voice_id']

        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}/stream-input?model_id=eleven_monolingual_v1&output_format=pcm_44100"

        async with wsclient.connect(uri) as ws:
            payload = {"text": f"{text} ", "try_trigger_generation": True}
            bos_message = {"text": " ", "xi_api_key": os.environ["ELEVENLABS_API_KEY"]}
            await ws.send(json.dumps(bos_message))
            await ws.send(json.dumps(payload))
            await ws.send(json.dumps({"text": ""}))

            remainder = b''
            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)

                    if data["audio"]:
                        chunk = base64.b64decode(data["audio"])

                        # pad chunk to fit 441 sample frames
                        if len(chunk) % (441 * 2) != 0:
                            print("NEIL padding chunk")
                            chunk = chunk + b'\x00' * (441 * 2 - len(chunk) % (441 * 2))

                        buf_arr = np.frombuffer(chunk, dtype=np.int16)

                        for i in range(0, buf_arr.shape[0] - 441, 441):
                            frame = livekit.AudioFrame.create(sample_rate=self._sample_rate, num_channels=1, samples_per_channel=441)
                            audio_data = np.ctypeslib.as_array(frame.data)
                            np.copyto(audio_data, buf_arr[i: i + 441])
                            resampled = frame.remix_and_resample(self._sample_rate, self._num_channels)
                            await self._audio_source.capture_frame(resampled)
                    else:
                        print("No audio data in the response")
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
