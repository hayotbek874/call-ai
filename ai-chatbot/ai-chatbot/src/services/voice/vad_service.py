import audioop
from collections.abc import AsyncIterator

class VADService:
    def __init__(
        self,
        silence_threshold: int = 500,
        silence_duration_ms: int = 700,
        sample_rate: int = 16000,
        chunk_ms: int = 20,
    ):
        self._threshold = silence_threshold
        self._silence_chunks = silence_duration_ms // chunk_ms
        self._sample_rate = sample_rate
        self._chunk_ms = chunk_ms

    def is_speech(self, pcm_chunk: bytes) -> bool:
        rms = audioop.rms(pcm_chunk, 2)
        return rms > self._threshold

    async def detect_utterances(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        buffer = bytearray()
        silence_count = 0
        speaking = False
        async for chunk in audio_stream:
            if self.is_speech(chunk):
                speaking = True
                silence_count = 0
                buffer.extend(chunk)
            elif speaking:
                silence_count += 1
                buffer.extend(chunk)
                if silence_count >= self._silence_chunks:
                    yield bytes(buffer)
                    buffer.clear()
                    speaking = False
                    silence_count = 0
