import asyncio
import base64
import io
import json
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from src.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ToolCallFunction:
    name: str
    arguments: str

@dataclass
class ToolCall:

    id: str
    type: str = "function"
    function: ToolCallFunction = None

@dataclass
class GeminiMessage:

    content: str | None = None
    role: str = "assistant"
    tool_calls: list[ToolCall] | None = None

    def model_dump(self, exclude_none: bool = False) -> dict:
        result = {"role": self.role}
        if self.content is not None or not exclude_none:
            result["content"] = self.content
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in self.tool_calls
            ]
        return result

class GeminiClient:

    def __init__(
        self,
        api_key: str,
        chat_model: str = "gemini-2.5-flash",
        audio_model: str = "gemini-2.5-flash",
        tts_voice_ru: str = "Kore",
        tts_voice_uz: str = "Kore",
    ):
        self._api_key = api_key
        self._chat_model = chat_model
        self._audio_model = audio_model
        self._voices = {"ru": tts_voice_ru, "uz": tts_voice_uz}
        self._client = genai.Client(api_key=api_key)

    def _convert_messages_to_gemini(self, messages: list[dict]) -> tuple[str | None, list[types.Content]]:

        system_instruction = None
        contents: list[types.Content] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
            elif role == "assistant":
                if content:
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=content)]
                    ))
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        args = func.get("arguments", "{}")
                        if isinstance(args, str):
                            args = json.loads(args) if args else {}
                        contents.append(types.Content(
                            role="model",
                            parts=[types.Part.from_function_call(
                                name=func.get("name", ""),
                                args=args
                            )]
                        ))
            elif role == "tool":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=msg.get("name", "unknown"),
                        response={"result": content}
                    )]
                ))
            else:
                if content:
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)]
                    ))

        return system_instruction, contents

    def _convert_tools_to_gemini(self, tools: list[dict]) -> list[types.Tool]:

        declarations = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                declarations.append(types.FunctionDeclaration(
                    name=func["name"],
                    description=func.get("description", ""),
                    parameters=func.get("parameters", {"type": "object", "properties": {}})
                ))
        return [types.Tool(function_declarations=declarations)] if declarations else []

    def _parse_response(self, response) -> GeminiMessage:

        if not response.candidates:
            return GeminiMessage(content="")

        candidate = response.candidates[0]
        content_parts = candidate.content.parts if candidate.content else []

        text_parts = []
        tool_calls = []

        for i, part in enumerate(content_parts):
            if part.text:
                text_parts.append(part.text)
            elif part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    id=f"call_{i}",
                    function=ToolCallFunction(
                        name=fc.name,
                        arguments=json.dumps(dict(fc.args) if fc.args else {})
                    )
                ))

        return GeminiMessage(
            content=" ".join(text_parts) if text_parts else None,
            tool_calls=tool_calls if tool_calls else None,
        )

    async def chat_stream(self, messages: list[dict], max_tokens: int = 120) -> AsyncIterator[str]:

        await logger.info("gemini_chat_stream", model=self._chat_model, messages_count=len(messages))

        system_instruction, contents = self._convert_messages_to_gemini(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=0.4,
        )

        response = self._client.models.generate_content(
            model=self._chat_model,
            contents=contents,
            config=config,
        )

        if response.text:
            for word in response.text.split():
                yield word + " "

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> GeminiMessage:

        await logger.info(
            "gemini_chat_with_tools",
            model=self._chat_model,
            messages_count=len(messages),
            tools_count=len(tools),
        )

        system_instruction, contents = self._convert_messages_to_gemini(messages)
        gemini_tools = self._convert_tools_to_gemini(tools)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
            tools=gemini_tools,
        )

        response = self._client.models.generate_content(
            model=self._chat_model,
            contents=contents,
            config=config,
        )

        msg = self._parse_response(response)
        await logger.info(
            "gemini_chat_with_tools_done",
            has_tool_calls=bool(msg.tool_calls),
            tool_calls_count=len(msg.tool_calls) if msg.tool_calls else 0,
        )
        return msg

    async def chat_with_tools_stream(
        self,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:

        await logger.info("gemini_chat_with_tools_stream", model=self._chat_model, messages_count=len(messages))

        system_instruction, contents = self._convert_messages_to_gemini(messages)
        gemini_tools = self._convert_tools_to_gemini(tools)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
            tools=gemini_tools,
        )

        response = self._client.models.generate_content(
            model=self._chat_model,
            contents=contents,
            config=config,
        )

        if response.text:
            for word in response.text.split():
                yield word + " "

    async def chat_complete(
        self,
        messages: list[dict],
        max_tokens: int = 800,
        temperature: float = 0.3,
    ) -> str:

        system_instruction, contents = self._convert_messages_to_gemini(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        response = self._client.models.generate_content(
            model=self._chat_model,
            contents=contents,
            config=config,
        )

        return response.text or ""

    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> str:

        await logger.info(
            "gemini_transcribe",
            model=self._audio_model,
            language=language,
            audio_size=len(audio_bytes),
        )

        if audio_bytes[:4] == b"RIFF":
            mime_type = "audio/wav"
        elif audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
            mime_type = "audio/mp3"
        else:
            mime_type = "audio/wav"

        lang_hint = f" The audio is in {'Russian' if language == 'ru' else 'Uzbek' if language == 'uz' else 'Russian or Uzbek'}." if language else ""

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    types.Part.from_text(
                        text=f"Transcribe this audio accurately. Output ONLY the transcription text, nothing else.{lang_hint}"
                    )
                ]
            )
        ]

        config = types.GenerateContentConfig(
            max_output_tokens=500,
            temperature=0.1,
        )

        response = self._client.models.generate_content(
            model=self._audio_model,
            contents=contents,
            config=config,
        )

        text = response.text or ""
        await logger.info("gemini_transcribed", text_len=len(text), text_preview=text[:50])
        return text.strip()

    async def tts_stream(self, text: str, language: str) -> AsyncIterator[bytes]:

        voice = self._voices.get(language, "Kore")
        await logger.info("gemini_tts", voice=voice, language=language, text_len=len(text))

        async for chunk in self._generate_speech(text, voice):
            yield chunk

    async def tts_stream_pcm(self, text: str, language: str) -> AsyncIterator[bytes]:

        voice = self._voices.get(language, "Kore")
        await logger.info("gemini_tts_pcm", voice=voice, language=language, text_len=len(text))

        async for chunk in self._generate_speech(text, voice):
            yield chunk

    async def _generate_speech(self, text: str, voice: str) -> AsyncIterator[bytes]:

        try:

            live_model = "gemini-2.5-flash-native-audio-latest"

            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                )
            )

            async with self._client.aio.live.connect(model=live_model, config=config) as session:

                await session.send_client_content(
                    turns=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                    turn_complete=True,
                )

                async for response in session.receive():

                    if response.server_content and response.server_content.turn_complete:
                        await logger.debug("gemini_tts_turn_complete")
                        break

                    if response.data:
                        yield response.data
                    elif response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                yield part.inline_data.data

        except Exception as e:
            await logger.error("gemini_tts_error", error=str(e), error_type=type(e).__name__)
            raise

    async def summarize(self, messages: list[dict]) -> str:

        await logger.info("gemini_summarize", model=self._chat_model, messages_count=len(messages))
        return await self.chat_complete(messages, max_tokens=200, temperature=0.3)
