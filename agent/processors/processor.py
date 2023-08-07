from enum import Enum

class ProcessorType(Enum):
    Audio = 1 << 0
    Video = 1 << 1


# TODO: should processor results be more efficient than a class alloc
class AudioProcessorResult:
    def __init__(self, frame: bytes, track_sid: str):
        self.frame = frame
        self.track_sid = track_sid


# TODO: should processor results be more efficient than a class alloc
class VideoProcessorResult:
    def __init__(self, frame: bytes, track_sid: str):
        self.frame = frame
        self.track_sid = track_sid


class Processor:
    def get_name(self) -> str:
        raise NotImplementedError

    def get_type(self) -> ProcessorType:
        raise NotImplementedError


class VideoProcessor(Processor):
    def get_type(self) -> ProcessorType:
        return ProcessorType.Video

    def process_video(self, track_sid: str, frame: bytes) -> bytes:
        raise NotImplementedError


class AudioProcessor(Processor):
    def get_type(self) -> ProcessorType:
        return ProcessorType.Audio

    def process_audio(self, track_sid: str, frame: bytes) -> bytes:
        raise NotImplementedError


class AudioVideoProcessor():
    def get_type(self) -> ProcessorType:
        return ProcessorType.Audio | ProcessorType.Video

    def process_video(self, participant_identity: str, track_sid: str, frame: bytes) -> ProcessorResult:
        raise NotImplementedError

    def process_audio(self, participant_identity: str, track_sid: str, frame: bytes) -> ProcessorResult:
        raise NotImplementedError

    