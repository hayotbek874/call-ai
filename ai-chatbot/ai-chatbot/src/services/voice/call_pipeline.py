import asyncio
from collections.abc import Awaitable, Callable

from src.core.logging import get_logger, mask_phone
from src.services.voice.audio_converter import AudioConverter
from src.services.voice.audiosocket_server import (
    FRAME_AUDIO,
    FRAME_HANGUP,
    build_audio_frame,
    build_hangup_frame,
    read_frame,
)
from src.services.voice.call_session import CallSession
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService
from src.services.voice.vad_service import VADService

logger = get_logger(__name__)

GetResponseFn = Callable[[str, str, str], Awaitable[str]]

FRAME_SIZE_BYTES: int = 320

SILENCE_FRAMES_END: int = 35

SILENCE_FRAMES_PROMPT: int = 1500

class CallPipeline:

    def __init__(
        self,
        session: CallSession,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        get_response: GetResponseFn,
        stt: STTService,
        tts: TTSService,
        vad: VADService,
        converter: AudioConverter,
        ai_semaphore: asyncio.Semaphore,
        call_max_duration: int = 600,
    ):
        self._session = session
        self._reader = reader
        self._writer = writer
        self._get_response = get_response
        self._stt = stt
        self._tts = tts
        self._vad = vad
        self._converter = converter
        self._ai_sem = ai_semaphore
        self._max_duration = call_max_duration

        self._utterance_q: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._barge_in = asyncio.Event()
        self._is_speaking_tts = False
        self._write_lock = asyncio.Lock()

    async def run(self) -> None:

        await logger.info(
            "pipeline_start",
            uuid=self._session.uuid,
            phone=mask_phone(self._session.phone),
        )
        try:
            try:
                await self._send_greeting()
                await logger.info(
                    "pipeline_greeting_done",
                    uuid=self._session.uuid,
                )
            except Exception as e:
                await logger.error(
                    "pipeline_greeting_failed",
                    uuid=self._session.uuid,
                    error=str(e),
                    error_type=type(e).__name__,
                )

            await asyncio.wait_for(
                asyncio.gather(
                    self._read_loop(),
                    self._process_loop(),
                ),
                timeout=self._max_duration,
            )
        except asyncio.TimeoutError:
            await logger.info(
                "pipeline_timeout",
                uuid=self._session.uuid,
                max_seconds=self._max_duration,
            )
            await self._say_and_hangup(
                "Извините, максимальное время звонка истекло. До свидания!"
                if self._session.language == "ru"
                else "Kechirasiz, qo'ng'iroq vaqti tugadi. Xayr!"
            )
        except (EOFError, ConnectionResetError, asyncio.IncompleteReadError):
            await logger.info("pipeline_disconnect", uuid=self._session.uuid)
        except Exception as e:
            await logger.error(
                "pipeline_error",
                uuid=self._session.uuid,
                error=str(e),
            )
        finally:
            self._session.is_active = False
            await self._utterance_q.put(None)
            await logger.info(
                "pipeline_end",
                uuid=self._session.uuid,
                duration=f"{self._session.duration:.1f}s",
            )

    async def _read_loop(self) -> None:
        buffer = bytearray()
        speaking = False
        silence_count = 0
        total_silence = 0

        while self._session.is_active:
            frame_type, payload = await read_frame(self._reader)

            if frame_type == FRAME_HANGUP:
                await logger.info("hangup_frame", uuid=self._session.uuid)
                self._session.is_active = False
                break

            if frame_type != FRAME_AUDIO:
                continue

            is_speech = self._vad.is_speech(payload)

            if is_speech and self._is_speaking_tts:
                self._barge_in.set()
                self._is_speaking_tts = False
                await logger.debug("barge_in", uuid=self._session.uuid)

            if is_speech:
                speaking = True
                silence_count = 0
                total_silence = 0
                buffer.extend(payload)
            elif speaking:
                silence_count += 1
                buffer.extend(payload)
                if silence_count >= SILENCE_FRAMES_END:

                    await self._utterance_q.put(bytes(buffer))
                    buffer.clear()
                    speaking = False
                    silence_count = 0
            else:
                total_silence += 1
                if total_silence >= SILENCE_FRAMES_PROMPT and not self._is_speaking_tts:
                    total_silence = 0
                    await self._say(
                        "Вы ещё на линии?"
                        if self._session.language == "ru"
                        else "Siz hali aloqadasizmi?"
                    )

    async def _process_loop(self) -> None:
        while self._session.is_active:
            try:
                audio_data = await asyncio.wait_for(
                    self._utterance_q.get(), timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue

            if audio_data is None:
                break

            await logger.info(
                "utterance_queued",
                uuid=self._session.uuid,
                audio_bytes=len(audio_data),
            )

            async with self._ai_sem:
                await self._process_utterance(audio_data)

    async def _process_utterance(self, pcm_8k: bytes) -> None:

        await logger.info(
            "process_utterance_start",
            uuid=self._session.uuid,
            phone=mask_phone(self._session.phone),
            pcm_bytes=len(pcm_8k),
            current_language=self._session.language,
        )

        wav_data = self._converter.pcm_to_wav(pcm_8k, sample_rate=8000)
        await logger.debug(
            "pcm_to_wav_conversion",
            uuid=self._session.uuid,
            wav_bytes=len(wav_data),
        )

        await logger.info(
            "stt_transcribe_start",
            uuid=self._session.uuid,
            current_language=self._session.language,
        )

        text = await self._stt.transcribe(wav_data, language=None)

        if not text or not text.strip():
            await logger.debug("stt_empty", uuid=self._session.uuid)
            return

        await logger.info(
            "stt_result",
            uuid=self._session.uuid,
            phone=mask_phone(self._session.phone),
            text=text[:100],
            text_len=len(text),
            language=self._session.language,
        )

        from src.utils.lang_detect import detect_language
        detected_lang = await detect_language(text)

        await logger.info(
            "language_detection_result",
            uuid=self._session.uuid,
            user_text=text[:80],
            detected_lang=detected_lang,
            current_lang=self._session.language,
        )

        if detected_lang != "both" and detected_lang != self._session.language:
            await logger.info(
                "language_switch_detected",
                uuid=self._session.uuid,
                phone=mask_phone(self._session.phone),
                old_language=self._session.language,
                new_language=detected_lang,
                user_text=text[:50],
            )
            self._session.language = detected_lang

        await logger.info(
            "ai_request_start",
            uuid=self._session.uuid,
            phone=mask_phone(self._session.phone),
            user_message=text,
            language=self._session.language,
        )

        try:
            response = await self._get_response(
                self._session.phone, text, self._session.language,
            )

            await logger.info(
                "ai_request_success",
                uuid=self._session.uuid,
                phone=mask_phone(self._session.phone),
                response=response[:200],
                response_len=len(response),
            )
        except Exception as e:
            await logger.error(
                "ai_error",
                uuid=self._session.uuid,
                phone=mask_phone(self._session.phone),
                error=str(e),
                error_type=type(e).__name__,
            )
            response = (
                "Извините, произошла ошибка. Пожалуйста, повторите."
                if self._session.language == "ru"
                else "Kechirasiz, xatolik yuz berdi. Iltimos, qaytadan ayting."
            )

        if not response or not response.strip():
            await logger.warning(
                "ai_empty_response",
                uuid=self._session.uuid,
            )
            return

        await logger.info(
            "ai_response",
            uuid=self._session.uuid,
            response_len=len(response),
        )

        order_complete_markers = [
            "заказ оформлен", "заказ создан", "заказ принят",
            "buyurtma qabul", "buyurtma rasmiylashtirildi", "buyurtma yaratildi",
            "спасибо, до свидания", "rahmat, xayr",
        ]
        is_order_complete = any(
            marker in response.lower() for marker in order_complete_markers
        )

        if is_order_complete:
            await logger.info(
                "order_complete_hangup",
                uuid=self._session.uuid,
            )
            await self._say_and_hangup(response)
        else:

            await self._say(response)

        await logger.info(
            "process_utterance_complete",
            uuid=self._session.uuid,
        )

    async def _say(self, text: str) -> None:

        await logger.info(
            "tts_say_start",
            uuid=self._session.uuid,
            text_len=len(text),
            language=self._session.language,
        )
        self._barge_in.clear()
        self._is_speaking_tts = True
        chunk_count = 0
        total_pcm_bytes = 0
        try:
            async for tts_chunk in self._tts.synthesize_pcm_stream(
                text, self._session.language,
            ):
                if self._barge_in.is_set():
                    await logger.debug("tts_interrupted", uuid=self._session.uuid)
                    break

                chunk_count += 1

                pcm_8k = self._converter.resample_24k_to_8k(tts_chunk)
                total_pcm_bytes += len(pcm_8k)
                await self._write_audio(pcm_8k)

            await logger.info(
                "tts_say_done",
                uuid=self._session.uuid,
                chunks=chunk_count,
                pcm_bytes=total_pcm_bytes,
            )
        except Exception as e:
            await logger.error(
                "tts_say_error",
                uuid=self._session.uuid,
                error=str(e),
                error_type=type(e).__name__,
                chunks_before_error=chunk_count,
            )
            raise
        finally:
            self._is_speaking_tts = False

    async def _send_greeting(self) -> None:
        await logger.info(
            "greeting_start",
            uuid=self._session.uuid,
            language=self._session.language,
        )

        self._session.language = "uz"
        await self._say(
            "Assalomu alaykum, Zargarshopga xush kelibsiz! "
            "Здравствуйте, добро пожаловать в ЗаргарШоп! "
            "Sizga qanday zargarlik kerak?"
        )

    async def _say_and_hangup(self, text: str) -> None:
        await self._say(text)
        await self._write_raw(build_hangup_frame())
        self._session.is_active = False

    async def _write_audio(self, pcm_8k: bytes) -> None:

        offset = 0
        while offset < len(pcm_8k):
            chunk = pcm_8k[offset : offset + FRAME_SIZE_BYTES]

            if len(chunk) < FRAME_SIZE_BYTES:
                chunk = chunk + b"\x00" * (FRAME_SIZE_BYTES - len(chunk))
            frame = build_audio_frame(chunk)
            await self._write_raw(frame)
            offset += FRAME_SIZE_BYTES

            await asyncio.sleep(0.018)

    async def _write_raw(self, data: bytes) -> None:
        async with self._write_lock:
            self._writer.write(data)
            await self._writer.drain()

    @staticmethod
    async def send_busy_and_close(
        writer: asyncio.StreamWriter,
        tts: TTSService,
        converter: AudioConverter,
        language: str = "ru",
    ) -> None:

        busy_text = (
            "К сожалению, все операторы заняты. Перезвоните позже."
            if language == "ru"
            else "Kechirasiz, barcha operatorlar band. Keyinroq qo'ng'iroq qiling."
        )
        try:
            async for chunk in tts.synthesize_pcm_stream(busy_text, language):
                pcm_8k = converter.resample_24k_to_8k(chunk)
                offset = 0
                while offset < len(pcm_8k):
                    c = pcm_8k[offset : offset + FRAME_SIZE_BYTES]
                    if len(c) < FRAME_SIZE_BYTES:
                        c = c + b"\x00" * (FRAME_SIZE_BYTES - len(c))
                    writer.write(build_audio_frame(c))
                    await writer.drain()
                    offset += FRAME_SIZE_BYTES
                    await asyncio.sleep(0.018)
            writer.write(build_hangup_frame())
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
