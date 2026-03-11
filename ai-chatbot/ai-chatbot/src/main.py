from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.v1.router import v1_router
from src.clients.asterisk_client import AsteriskClient
from src.clients.crm_client import CRMClient
from src.clients.gemini_client import GeminiClient
from src.clients.openai_client import OpenAIClient
from src.core.config import settings
from src.core.logging import get_logger, setup_logging
from src.middlewares.logging import LoggingMiddleware
from src.middlewares.rate_limit import RateLimitMiddleware
from src.providers.main_provider import MainProvider
from src.services.ai.crm_service import CRMService
from src.services.ai.tools import ToolExecutor
from src.services.voice.asterisk_service import AsteriskService
from src.services.voice.audio_converter import AudioConverter
from src.services.voice.call_session import CallSessionManager
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService
from src.services.voice.vad_service import VADService
from src.ari.config import ARIConfig
from src.ari.dispatcher import ARIEventDispatcher
from src.ari.rest_client import ARIRestClient
from src.ari.service import ARIService as ARIAppService
from src.ari.session_manager import ARISessionManager

setup_logging()
logger = get_logger(__name__)

engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_pre_ping=True,
)
redis_client = aioredis.from_url(settings.REDIS_URL)
container = make_async_container(MainProvider(engine=engine, redis=redis_client))

def _build_asterisk_service() -> AsteriskService:
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
    )
    openai_client = OpenAIClient(
        api_key=settings.OPENAI_API_KEY,
        chat_model=settings.OPENAI_CHAT_MODEL,
        stt_model=settings.OPENAI_STT_MODEL,
        tts_model=settings.OPENAI_TTS_MODEL,
        tts_voice_ru=settings.OPENAI_TTS_VOICE_RU,
        tts_voice_uz=settings.OPENAI_TTS_VOICE_UZ,
    )
    gemini_client = GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        chat_model=settings.GEMINI_CHAT_MODEL,
        audio_model=settings.GEMINI_AUDIO_MODEL,
        tts_voice_ru=settings.GEMINI_VOICE_RU,
        tts_voice_uz=settings.GEMINI_VOICE_UZ,
    )
    crm = CRMClient(crm_url=settings.CRM_BASE_URL, api_key=settings.CRM_API_KEY)
    crm_service = CRMService(crm, redis_client)
    tool_executor = ToolExecutor(crm_service)
    asterisk_client = AsteriskClient(
        base_url=f"http://{settings.ASTERISK_HOST}:{settings.ASTERISK_PORT}",
        login=settings.ASTERISK_ARI_USER,
        password=settings.ASTERISK_ARI_PASSWORD,
        redis=redis_client,
        client_name="asterisk",
    )
    return AsteriskService(
        session_factory=session_factory,
        redis=redis_client,
        openai=openai_client,
        tool_executor=tool_executor,
        stt=STTService(gemini_client),
        tts=TTSService(gemini_client),
        vad=VADService(),
        converter=AudioConverter(),
        asterisk=asterisk_client,
        call_session_manager=CallSessionManager(
            max_concurrent=settings.MAX_CONCURRENT_CALLS,
        ),
        host=settings.AUDIOSOCKET_HOST,
        port=settings.AUDIOSOCKET_PORT,
        ai_concurrency=settings.OPENAI_VOICE_CONCURRENCY,
        call_max_duration=settings.CALL_MAX_DURATION,
    )

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await logger.info("app_starting", app_name=settings.APP_NAME, version=settings.APP_VERSION)
    await redis_client.ping()

    asterisk_service = _build_asterisk_service()
    await asterisk_service.start()
    app.state.asterisk_service = asterisk_service

    ari_config = ARIConfig.from_settings()
    ari_rest = ARIRestClient(ari_config)
    ari_sessions = ARISessionManager(max_concurrent=settings.MAX_CONCURRENT_CALLS)
    ari_dispatcher = ARIEventDispatcher()
    ari_service = ARIAppService(
        config=ari_config,
        rest_client=ari_rest,
        session_manager=ari_sessions,
        dispatcher=ari_dispatcher,
    )
    await ari_service.start()
    app.state.ari_service = ari_service

    await logger.info("app_started", db="connected", redis="connected", voice="listening", ari="connected")
    app.state.engine = engine
    app.state.redis = redis_client
    yield
    await logger.info("app_shutting_down")
    await ari_service.stop()
    await asterisk_service.stop()
    await container.close()
    await redis_client.aclose()
    await engine.dispose()
    await logger.info("app_stopped")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
setup_dishka(container, app)
app.include_router(v1_router, prefix="/api/v1")

import pathlib

from fastapi.responses import HTMLResponse

_static_dir = pathlib.Path(__file__).parent / "static"

@app.get("/voice", response_class=HTMLResponse, include_in_schema=False)
async def voice_page():
    return (_static_dir / "voice.html").read_text(encoding="utf-8")
