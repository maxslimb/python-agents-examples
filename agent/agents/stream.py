import threading
import livekit
import asyncio
from typing import TypeVar, Generic

STREAM_TYPE = TypeVar("STREAM_TYPE", livekit.VideoStream, livekit.AudioStream)
FRAME_TYPE = TypeVar("FRAME_TYPE", livekit.VideoFrame, livekit.AudioFrame)

class Stream(Generic[STREAM_TYPE, FRAME_TYPE]):
    def __init__(self, stream: STREAM_TYPE):
        self.video_stream = stream
        self.video_stream.on("frame_received", self.__on_frame_received)
        self.queue: asyncio.Queue[FRAME_TYPE] = asyncio.Queue()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return self.queue.get()

    def __on_frame_received(self, frame: FRAME_TYPE):
        self.queue.put_nowait(frame)

class VideoStream(Stream[livekit.VideoStream, livekit.VideoFrame]):
    pass

class AudioStream(Stream[livekit.AudioStream, livekit.AudioFrame]):
    pass
