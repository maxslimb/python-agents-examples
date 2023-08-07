from processors import AudioProcessor

class TransciptionProcessor(AudioProcessor):
    def __init__(self):
        pass

    def get_name(self) -> str:
        return "transcription"

    def process_audio(self, track_sid: str, frame: bytes) -> bytes:
        return frame