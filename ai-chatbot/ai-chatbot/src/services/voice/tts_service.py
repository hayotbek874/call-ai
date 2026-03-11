from collections.abc import AsyncIterator

from src.clients.gemini_client import GeminiClient
from src.core.logging import get_logger

logger = get_logger(__name__)

class TTSService:
    def __init__(self, gemini_client: GeminiClient):
        self._gemini = gemini_client

    async def synthesize_stream(self, text: str, language: str) -> AsyncIterator[bytes]:

        await logger.info("tts_synthesize", language=language, text_len=len(text))
        chunk_count = 0
        async for chunk in self._gemini.tts_stream(text, language):
            chunk_count += 1
            yield chunk
        await logger.info("tts_done", language=language, chunks=chunk_count)

    async def synthesize_pcm_stream(self, text: str, language: str) -> AsyncIterator[bytes]:

        await logger.info("tts_synthesize_pcm", language=language, text_len=len(text))
        chunk_count = 0
        async for chunk in self._gemini.tts_stream_pcm(text, language):
            chunk_count += 1
            yield chunk
        await logger.info("tts_pcm_done", language=language, chunks=chunk_count)
