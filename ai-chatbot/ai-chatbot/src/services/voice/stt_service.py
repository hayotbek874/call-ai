from src.clients.gemini_client import GeminiClient
from src.core.logging import get_logger

logger = get_logger(__name__)

class STTService:
    def __init__(self, gemini_client: GeminiClient):
        self._gemini = gemini_client

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:

        await logger.info(
            "stt_transcribe_request",
            language=language or "auto-detect",
            audio_size=len(audio_bytes),
            audio_format=self._detect_format(audio_bytes),
        )

        text = await self._gemini.transcribe(audio_bytes, language)

        await logger.info(
            "stt_transcribe_response",
            language=language or "auto-detect",
            text_len=len(text),
            text_preview=text[:100] if text else "",
        )
        return text

    def _detect_format(self, audio_bytes: bytes) -> str:

        if audio_bytes[:4] == b"RIFF":
            return "wav"
        elif audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
            return "mp3"
        else:
            return "webm"
