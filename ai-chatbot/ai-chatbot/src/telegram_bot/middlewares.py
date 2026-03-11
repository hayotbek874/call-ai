from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.crm_client import CRMClient
from src.clients.openai_client import OpenAIClient
from src.core.logging import get_logger
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.user_repository import UserRepository
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.services.ai.context_service import ContextService
from src.services.ai.crm_service import CRMService
from src.services.ai.tools import ToolExecutor
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService

logger = get_logger(__name__)

class DbSessionMiddleware(BaseMiddleware):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Redis,
        openai: OpenAIClient,
        tool_executor: ToolExecutor,
        stt_svc: STTService,
        tts_svc: TTSService,
        crm_client: CRMClient,
    ) -> None:
        super().__init__()
        self._session_factory = session_factory
        self._redis = redis
        self._openai = openai
        self._tool_executor = tool_executor
        self._stt_svc = stt_svc
        self._tts_svc = tts_svc
        self._crm_client = crm_client
        self._crm_service = CRMService(crm_client, redis)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._session_factory() as session, session.begin():
            user_repo = UserRepository(session)
            conv_repo = ConversationRepository(session)
            context_svc = ContextService(self._redis, conv_repo, self._openai)
            orchestrator = ChatOrchestrator(
                self._openai,
                context_svc,
                self._tool_executor,
                self._stt_svc,
                self._tts_svc,
            )

            data["user_repo"] = user_repo
            data["conv_repo"] = conv_repo
            data["orchestrator"] = orchestrator
            data["session"] = session
            data["stt_svc"] = self._stt_svc
            data["tts_svc"] = self._tts_svc
            data["crm_client"] = self._crm_client
            data["crm_service"] = self._crm_service

            return await handler(event, data)
