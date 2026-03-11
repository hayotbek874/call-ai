import asyncio

import redis.asyncio as aioredis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.clients.gemini_client import GeminiClient
from src.clients.openai_client import OpenAIClient
from src.clients.crm_client import CRMClient
from src.core.config import settings
from src.core.logging import get_logger, setup_logging
from src.services.ai.crm_service import CRMService
from src.services.ai.tools import ToolExecutor
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService
from src.telegram_bot.middlewares import DbSessionMiddleware
from src.telegram_bot.routers import chat_router, order_router, phone_router, start_router

setup_logging()
logger = get_logger(__name__)

async def main() -> None:
    await logger.info("telegram_bot_starting")
    engine = create_async_engine(
        settings.POSTGRES_URL,
        pool_size=settings.POOL_SIZE,
        max_overflow=settings.MAX_OVERFLOW,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    redis = aioredis.from_url(settings.REDIS_URL)
    await redis.ping()
    await logger.info("telegram_bot_infra_ready", db="connected", redis="connected")

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
    crm_client = CRMClient(
        crm_url=settings.CRM_BASE_URL,
        api_key=settings.CRM_API_KEY,
    )
    crm_service = CRMService(crm_client, redis)
    tool_executor = ToolExecutor(crm_service)
    stt_svc = STTService(gemini_client)
    tts_svc = TTSService(gemini_client)
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    fsm_storage = RedisStorage(redis)
    dp = Dispatcher(storage=fsm_storage)

    middleware = DbSessionMiddleware(
        session_factory=session_factory,
        redis=redis,
        openai=openai_client,
        tool_executor=tool_executor,
        stt_svc=stt_svc,
        tts_svc=tts_svc,
        crm_client=crm_client,
    )
    dp.message.middleware(middleware)

    dp.include_router(start_router)
    dp.include_router(phone_router)
    dp.include_router(order_router)
    dp.include_router(chat_router)

    await logger.info("telegram_bot_polling")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis.aclose()
        await engine.dispose()
        await logger.info("telegram_bot_stopped")

if __name__ == "__main__":
    asyncio.run(main())
