import asyncio
import json
from collections.abc import AsyncIterator

from src.clients.openai_client import OpenAIClient
from src.core.logging import get_logger, mask_phone
from src.services.ai.context_service import ContextService
from src.services.ai.tools import TOOLS, ToolExecutor
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService

logger = get_logger(__name__)

MAX_TOOL_ROUNDS = 5

class ChatOrchestrator:
    def __init__(
        self,
        openai: OpenAIClient,
        context: ContextService,
        tool_executor: ToolExecutor,
        stt: STTService,
        tts: TTSService,
    ):
        self._openai = openai
        self._context = context
        self._tools = tool_executor
        self._stt = stt
        self._tts = tts

    async def process_text(
        self, phone: str, message: str, language: str, channel: str,
    ) -> AsyncIterator[str]:
        await logger.info(
            "process_text_start",
            phone=mask_phone(phone),
            language=language,
            channel=channel,
            message_len=len(message),
        )

        messages = await self._context.build_messages(phone, language, message, None, channel)
        max_tokens = 150 if channel == "voice" else 800
        messages, tool_calls_log = await self._run_tool_loop(messages, phone, max_tokens)

        if tool_calls_log:
            yield f"__TOOL_CALLS__:{json.dumps(tool_calls_log)}"

        full = ""
        async for token in self._openai.chat_with_tools_stream(
            messages, TOOLS, max_tokens=max_tokens, temperature=0.4,
        ):
            full += token
            yield token

        await self._context.append(phone, "user", message, channel=channel)
        await self._context.append(phone, "assistant", full, channel=channel)
        await logger.info(
            "process_text_done",
            phone=mask_phone(phone),
            response_len=len(full),
        )

    async def get_text_response(
        self, phone: str, message: str, language: str, channel: str,
    ) -> str:
        await logger.info(
            "get_text_response_start",
            phone=mask_phone(phone),
            message=message,
            language=language,
            channel=channel,
        )

        text, tools_used = await self.get_text_response_with_tools(phone, message, language, channel)

        await logger.info(
            "get_text_response_complete",
            phone=mask_phone(phone),
            response=text[:200],
            response_len=len(text),
            tools_used=len(tools_used),
        )

        return text

    async def get_text_response_with_tools(
        self, phone: str, message: str, language: str, channel: str,
    ) -> tuple[str, list[dict]]:
        text_parts: list[str] = []
        tool_calls_log: list[dict] = []
        async for token in self.process_text(phone, message, language, channel):
            if token.startswith("__TOOL_CALLS__:"):
                tool_calls_log = json.loads(token.removeprefix("__TOOL_CALLS__:"))
            else:
                text_parts.append(token)
        return "".join(text_parts), tool_calls_log

    async def process_voice(
        self, phone: str, audio_bytes: bytes, language: str,
    ) -> AsyncIterator[bytes]:
        await logger.info(
            "process_voice_start",
            phone=mask_phone(phone),
            language=language,
            audio_size=len(audio_bytes),
        )

        text = await self._stt.transcribe(audio_bytes, language)
        await logger.info("voice_transcribed", phone=mask_phone(phone), text_len=len(text))

        messages = await self._context.build_messages(phone, language, text, None, "voice")
        messages, _tool_log = await self._run_tool_loop(messages, phone, max_tokens=150)

        sentence_q: asyncio.Queue[str | None] = asyncio.Queue()
        audio_q: asyncio.Queue[bytes | None] = asyncio.Queue()

        gpt_task = asyncio.create_task(
            self._fill_sentence_queue(messages, sentence_q),
        )
        tts_task = asyncio.create_task(
            self._fill_audio_queue(sentence_q, audio_q, language),
        )

        async for chunk in self._drain(audio_q):
            yield chunk

        await gpt_task
        await tts_task

        await self._context.append(phone, "user", text, channel="voice")
        await logger.info("process_voice_done", phone=mask_phone(phone))

    async def _run_tool_loop(
        self,
        messages: list[dict],
        phone: str,
        max_tokens: int = 800,
    ) -> tuple[list[dict], list[dict]]:
        tool_calls_log: list[dict] = []

        await logger.info(
            "tool_loop_start",
            phone=mask_phone(phone),
            messages_count=len(messages),
            max_rounds=MAX_TOOL_ROUNDS,
        )

        for round_n in range(MAX_TOOL_ROUNDS):
            await logger.debug(
                "tool_loop_calling_gpt",
                phone=mask_phone(phone),
                round=round_n + 1,
                tools_available=len(TOOLS),
            )

            assistant_msg = await self._openai.chat_with_tools(
                messages, TOOLS, max_tokens=max_tokens, temperature=0.3,
            )

            if not assistant_msg.tool_calls:
                await logger.info(
                    "tool_loop_no_more_tools",
                    phone=mask_phone(phone),
                    round=round_n + 1,
                    final_response_preview=assistant_msg.content[:100] if assistant_msg.content else "",
                )
                break

            messages.append(assistant_msg.model_dump(exclude_none=True))

            call_names = [tc.function.name for tc in assistant_msg.tool_calls]
            await logger.info(
                "tool_loop_round",
                phone=mask_phone(phone),
                round=round_n + 1,
                tool_calls=call_names,
                tool_count=len(call_names),
            )

            async def _exec_one(tc):
                args = json.loads(tc.function.arguments)
                await logger.info(
                    "tool_execute_request",
                    phone=mask_phone(phone),
                    tool=tc.function.name,
                    args=args,
                )
                result = await self._tools.execute(tc.function.name, args)
                await logger.info(
                    "tool_execute_response",
                    phone=mask_phone(phone),
                    tool=tc.function.name,
                    result_len=len(result),
                    result_preview=result[:150] if result else "",
                )
                tool_calls_log.append({
                    "tool": tc.function.name,
                    "args": args,
                    "result_preview": result[:200] if result else "",
                })
                return {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }

            tool_results = await asyncio.gather(
                *[_exec_one(tc) for tc in assistant_msg.tool_calls],
            )

            messages.extend(tool_results)

        await logger.info(
            "tool_loop_complete",
            phone=mask_phone(phone),
            total_tool_calls=len(tool_calls_log),
            tools_used=[t["tool"] for t in tool_calls_log],
        )
        return messages, tool_calls_log

    async def _fill_sentence_queue(
        self, messages: list[dict], q: asyncio.Queue[str | None],
    ) -> None:
        buf = ""
        async for token in self._openai.chat_with_tools_stream(
            messages, TOOLS, max_tokens=150,
        ):
            buf += token
            for sep in (".", "!", "?", "\n"):
                if sep in buf:
                    parts = buf.split(sep, 1)
                    sentence = (parts[0] + sep).strip()
                    if sentence:
                        await q.put(sentence)
                    buf = parts[1]
        if buf.strip():
            await q.put(buf.strip())
        await q.put(None)

    async def _fill_audio_queue(
        self,
        sentence_q: asyncio.Queue[str | None],
        audio_q: asyncio.Queue[bytes | None],
        language: str,
    ) -> None:
        while True:
            sentence = await sentence_q.get()
            if sentence is None:
                break
            async for chunk in self._tts.synthesize_stream(sentence, language):
                await audio_q.put(chunk)
        await audio_q.put(None)

    async def _drain(self, q: asyncio.Queue[bytes | None]) -> AsyncIterator[bytes]:
        while True:
            chunk = await q.get()
            if chunk is None:
                break
            yield chunk
