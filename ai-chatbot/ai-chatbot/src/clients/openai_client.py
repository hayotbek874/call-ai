import io
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletionToolParam

from src.core.logging import get_logger

logger = get_logger(__name__)

class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        chat_model: str,
        stt_model: str,
        tts_model: str,
        tts_voice_ru: str,
        tts_voice_uz: str,
    ):
        self._client = AsyncOpenAI(api_key=api_key)
        self._chat_model = chat_model
        self._stt_model = stt_model
        self._tts_model = tts_model
        self._voices = {"ru": tts_voice_ru, "uz": tts_voice_uz}

    async def chat_stream(self, messages: list[dict], max_tokens: int = 120) -> AsyncIterator[str]:
        await logger.info(
            "openai_chat_stream",
            model=self._chat_model,
            messages_count=len(messages),
            max_tokens=max_tokens,
        )
        stream = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.4,
            stream=False,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[ChatCompletionToolParam],
        max_tokens: int = 800,
        temperature: float = 0.3,
        tool_choice: str | dict | None = "auto",
    ) -> ChatCompletionMessage:

        await logger.info(
            "openai_chat_with_tools",
            model=self._chat_model,
            messages_count=len(messages),
            tools_count=len(tools),
            tool_choice=str(tool_choice),
        )
        response = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        msg = response.choices[0].message
        await logger.info(
            "openai_chat_with_tools_done",
            has_tool_calls=bool(msg.tool_calls),
            tool_calls_count=len(msg.tool_calls) if msg.tool_calls else 0,
        )
        return msg

    async def chat_with_tools_stream(
        self,
        messages: list[dict],
        tools: list[ChatCompletionToolParam],
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:

        await logger.info(
            "openai_chat_with_tools_stream",
            model=self._chat_model,
            messages_count=len(messages),
        )
        stream = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def chat_complete(
        self,
        messages: list[dict],
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> str:

        response = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:
        await logger.info(
            "openai_transcribe",
            model=self._stt_model,
            language=language,
            audio_size=len(audio_bytes),
        )

        if audio_bytes[:4] == b"RIFF":
            fname, mime = "audio.wav", "audio/wav"
        elif audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
            fname, mime = "audio.mp3", "audio/mp3"
        else:
            fname, mime = "audio.webm", "audio/webm"
        file = (fname, io.BytesIO(audio_bytes), mime)

        kwargs: dict = {"model": self._stt_model, "file": file}
        if language:
            kwargs["language"] = language

        result = await self._client.audio.transcriptions.create(**kwargs)
        await logger.info("openai_transcribed", text_len=len(result.text))
        return result.text

    async def tts_stream(self, text: str, language: str) -> AsyncIterator[bytes]:
        voice = self._voices.get(language, "onyx")
        await logger.info("openai_tts", model=self._tts_model, voice=voice, language=language, text_len=len(text))
        response = await self._client.audio.speech.create(
            model=self._tts_model,
            voice=voice,
            input=text,
            response_format="mp3",
        )
        stream = response.aiter_bytes(chunk_size=4096)
        if hasattr(stream, "__await__"):
            stream = await stream
        async for chunk in stream:
            yield chunk

    async def tts_stream_pcm(self, text: str, language: str) -> AsyncIterator[bytes]:

        voice = self._voices.get(language, "onyx")
        await logger.info(
            "openai_tts_pcm", model=self._tts_model, voice=voice, language=language, text_len=len(text),
        )
        response = await self._client.audio.speech.create(
            model=self._tts_model,
            voice=voice,
            input=text,
            response_format="pcm",
        )

        stream = response.aiter_bytes(chunk_size=4800)
        if hasattr(stream, "__await__"):
            stream = await stream
        async for chunk in stream:
            yield chunk

    async def summarize(self, messages: list[dict]) -> str:
        await logger.info("openai_summarize", model=self._chat_model, messages_count=len(messages))
        result = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            max_tokens=200,
            temperature=0.3,
        )
        summary = result.choices[0].message.content
        await logger.info("openai_summarized", summary_len=len(summary))
        return summary
