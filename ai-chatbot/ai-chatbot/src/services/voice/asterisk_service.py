import asyncio

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.asterisk_client import AsteriskClient
from src.clients.openai_client import OpenAIClient
from src.core.logging import get_logger, mask_phone
from src.repositories.call_repository import CallRepository
from src.repositories.conversation_repository import ConversationRepository
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.services.ai.context_service import ContextService
from src.services.ai.tools import ToolExecutor
from src.services.voice.audio_converter import AudioConverter
from src.services.voice.audiosocket_server import AudioSocketServer
from src.services.voice.call_pipeline import CallPipeline
from src.services.voice.call_session import CallSessionManager
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService
from src.services.voice.vad_service import VADService

logger = get_logger(__name__)

class AsteriskService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Redis,
        openai: OpenAIClient,
        tool_executor: ToolExecutor,
        stt: STTService,
        tts: TTSService,
        vad: VADService,
        converter: AudioConverter,
        asterisk: AsteriskClient,
        call_session_manager: CallSessionManager,
        host: str = "0.0.0.0",
        port: int = 9099,
        ai_concurrency: int = 5,
        call_max_duration: int = 600,
    ):
        self._session_factory = session_factory
        self._redis = redis
        self._openai = openai
        self._tool_executor = tool_executor
        self._stt = stt
        self._tts = tts
        self._vad = vad
        self._converter = converter
        self._asterisk = asterisk
        self._sessions = call_session_manager
        self._ai_sem = asyncio.Semaphore(ai_concurrency)
        self._max_duration = call_max_duration

        self._server = AudioSocketServer(
            host=host,
            port=port,
            on_connection=self._on_connection,
        )

    async def start(self) -> None:
        await self._server.start()
        await logger.info("asterisk_service_started", active_calls=self._sessions.count)

    async def stop(self) -> None:
        await self._server.stop()
        for s in self._sessions.all_sessions():
            s.is_active = False
        await logger.info("asterisk_service_stopped")

    async def _on_connection(
        self,
        call_uuid: str,
        phone: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        await logger.info(
            "audiosocket_connection",
            call_uuid=call_uuid,
            phone=mask_phone(phone),
        )

        session = await self._sessions.register(call_uuid, phone)
        if session is None:
            await CallPipeline.send_busy_and_close(
                writer, self._tts, self._converter,
            )
            return

        call_id: int | None = None
        try:
            async with self._session_factory() as db, db.begin():
                call_repo = CallRepository(db)
                lang = await call_repo.get_user_language(phone) or "ru"
                call_record = await call_repo.create(
                    phone=phone, asterisk_call_id=call_uuid,
                )
                call_id = call_record.id
            session.language = lang
            session.call_db_id = call_id
        except Exception as e:
            await logger.error("call_db_init_error", error=str(e))
            session.language = "ru"

        try:
            async with self._session_factory() as db, db.begin():
                conv_repo = ConversationRepository(db)
                context = ContextService(self._redis, conv_repo, self._openai)
                await context.clear_channel(phone, "voice")
        except Exception as e:
            await logger.error("voice_ctx_clear_error", error=str(e))

        async def _get_response(ph: str, text: str, lang: str) -> str:
            async with self._session_factory() as db, db.begin():
                conv_repo = ConversationRepository(db)
                context = ContextService(self._redis, conv_repo, self._openai)
                orchestrator = ChatOrchestrator(
                    self._openai, context, self._tool_executor,
                    self._stt, self._tts,
                )
                return await orchestrator.get_text_response(
                    ph, text, lang, "voice",
                )

        pipeline = CallPipeline(
            session=session,
            reader=reader,
            writer=writer,
            get_response=_get_response,
            stt=self._stt,
            tts=self._tts,
            vad=self._vad,
            converter=self._converter,
            ai_semaphore=self._ai_sem,
            call_max_duration=self._max_duration,
        )

        try:
            await pipeline.run()
        finally:
            await self._sessions.unregister(call_uuid)

            if call_id is not None:
                try:
                    async with self._session_factory() as db, db.begin():
                        call_repo = CallRepository(db)
                        await call_repo.update(
                            call_id,
                            duration=int(session.duration),
                            status="answered",
                        )
                except Exception as e:
                    await logger.error("call_db_end_error", error=str(e))

            if phone:
                try:
                    async with self._session_factory() as db, db.begin():
                        conv_repo = ConversationRepository(db)
                        context = ContextService(
                            self._redis, conv_repo, self._openai,
                        )
                        await context.generate_summary(phone, channel="voice")
                except Exception as e:
                    await logger.error("call_summary_error", error=str(e))
