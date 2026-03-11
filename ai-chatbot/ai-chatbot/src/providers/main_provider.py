from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.clients.asterisk_client import AsteriskClient
from src.clients.click_client import ClickClient
from src.clients.crm_client import CRMClient
from src.clients.gemini_client import GeminiClient
from src.clients.instagram_client import InstagramClient
from src.clients.openai_client import OpenAIClient
from src.clients.payme_client import PaymeClient
from src.clients.telegram_client import TelegramClient
from src.core.config import settings
from src.repositories.admin_repository import AdminRepository
from src.repositories.call_repository import CallRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.order_repository import OrderRepository
from src.repositories.user_repository import UserRepository
from src.services.admin_service import AdminService
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.services.ai.context_service import ContextService
from src.services.ai.crm_service import CRMService
from src.services.ai.product_search_service import ProductSearchService
from src.services.ai.tools import ToolExecutor
from src.services.instagram_service import InstagramService
from src.services.telegram_service import TelegramBotService
from src.services.voice.asterisk_service import AsteriskService
from src.services.voice.audio_converter import AudioConverter
from src.services.voice.call_session import CallSessionManager
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService
from src.services.voice.vad_service import VADService

class MainProvider(Provider):
    def __init__(self, engine: AsyncEngine, redis: Redis):
        super().__init__()
        self._engine = engine
        self._redis = redis
        self._session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @provide(scope=Scope.APP)
    async def redis(self) -> Redis:
        return self._redis

    @provide(scope=Scope.REQUEST)
    async def db_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session, session.begin():
            yield session

    @provide(scope=Scope.APP)
    def gemini_client(self) -> GeminiClient:
        return GeminiClient(
            api_key=settings.GEMINI_API_KEY,
            chat_model=settings.GEMINI_CHAT_MODEL,
            audio_model=settings.GEMINI_AUDIO_MODEL,
            tts_voice_ru=settings.GEMINI_VOICE_RU,
            tts_voice_uz=settings.GEMINI_VOICE_UZ,
        )

    @provide(scope=Scope.APP)
    def openai_client(self) -> OpenAIClient:
        return OpenAIClient(
            api_key=settings.OPENAI_API_KEY,
            chat_model=settings.OPENAI_CHAT_MODEL,
            stt_model=settings.OPENAI_STT_MODEL,
            tts_model=settings.OPENAI_TTS_MODEL,
            tts_voice_ru=settings.OPENAI_TTS_VOICE_RU,
            tts_voice_uz=settings.OPENAI_TTS_VOICE_UZ,
        )

    @provide(scope=Scope.APP)
    def asterisk_client(self, redis: Redis) -> AsteriskClient:
        return AsteriskClient(
            base_url=f"http://{settings.ASTERISK_HOST}:{settings.ASTERISK_PORT}",
            login=settings.ASTERISK_ARI_USER,
            password=settings.ASTERISK_ARI_PASSWORD,
            redis=redis,
            client_name="asterisk",
        )

    @provide(scope=Scope.APP)
    def crm_client(self) -> CRMClient:
        return CRMClient(
            crm_url=settings.CRM_BASE_URL,
            api_key=settings.CRM_API_KEY,
        )

    @provide(scope=Scope.APP)
    def instagram_client(self, redis: Redis) -> InstagramClient:
        return InstagramClient(
            "https://graph.instagram.com",
            "",
            settings.INSTAGRAM_ACCESS_TOKEN,
            redis,
            "instagram",
        )

    @provide(scope=Scope.APP)
    def telegram_client(self, redis: Redis) -> TelegramClient:
        return TelegramClient(
            "https://api.telegram.org",
            "",
            settings.TELEGRAM_BOT_TOKEN,
            redis,
            "telegram",
        )

    @provide(scope=Scope.APP)
    def click_client(self, redis: Redis) -> ClickClient:
        return ClickClient(
            "https://api.click.uz",
            "",
            settings.CLICK_SECRET_KEY,
            redis,
            "click",
        )

    @provide(scope=Scope.APP)
    def payme_client(self, redis: Redis) -> PaymeClient:
        return PaymeClient(
            "https://checkout.paycom.uz",
            "",
            settings.PAYME_SECRET_KEY,
            redis,
            "payme",
        )

    @provide(scope=Scope.REQUEST)
    def admin_repo(self, session: AsyncSession) -> AdminRepository:
        return AdminRepository(session)

    @provide(scope=Scope.REQUEST)
    def admin_svc(self, repo: AdminRepository) -> AdminService:
        return AdminService(repo)

    @provide(scope=Scope.REQUEST)
    def user_repo(self, session: AsyncSession) -> UserRepository:
        return UserRepository(session)

    @provide(scope=Scope.REQUEST)
    def conversation_repo(self, session: AsyncSession) -> ConversationRepository:
        return ConversationRepository(session)

    @provide(scope=Scope.REQUEST)
    def call_repo(self, session: AsyncSession) -> CallRepository:
        return CallRepository(session)

    @provide(scope=Scope.REQUEST)
    def order_repo(self, session: AsyncSession) -> OrderRepository:
        return OrderRepository(session)

    @provide(scope=Scope.APP)
    def stt(self, gemini: GeminiClient) -> STTService:
        return STTService(gemini)

    @provide(scope=Scope.APP)
    def tts(self, gemini: GeminiClient) -> TTSService:
        return TTSService(gemini)

    @provide(scope=Scope.APP)
    def vad(self) -> VADService:
        return VADService()

    @provide(scope=Scope.APP)
    def audio_converter(self) -> AudioConverter:
        return AudioConverter()

    @provide(scope=Scope.APP)
    def call_session_manager(self) -> CallSessionManager:
        return CallSessionManager(max_concurrent=settings.MAX_CONCURRENT_CALLS)

    @provide(scope=Scope.APP)
    def crm_service(self, crm_client: CRMClient, redis: Redis) -> CRMService:
        return CRMService(crm_client, redis)

    @provide(scope=Scope.APP)
    def tool_executor(self, crm_service: CRMService) -> ToolExecutor:
        return ToolExecutor(crm_service)

    @provide(scope=Scope.APP)
    def product_search(self, crm_service: CRMService) -> ProductSearchService:
        return ProductSearchService(crm_service)

    @provide(scope=Scope.REQUEST)
    def context_svc(
        self, redis: Redis, repo: ConversationRepository, openai: OpenAIClient
    ) -> ContextService:
        return ContextService(redis, repo, openai)

    @provide(scope=Scope.REQUEST)
    def orchestrator(
        self,
        openai: OpenAIClient,
        context: ContextService,
        tool_executor: ToolExecutor,
        stt: STTService,
        tts: TTSService,
    ) -> ChatOrchestrator:
        return ChatOrchestrator(openai, context, tool_executor, stt, tts)

    @provide(scope=Scope.REQUEST)
    def asterisk_svc(
        self,
        asterisk: AsteriskClient,
        openai: OpenAIClient,
        tool_executor: ToolExecutor,
        stt: STTService,
        tts: TTSService,
        vad: VADService,
        converter: AudioConverter,
        call_session_manager: CallSessionManager,
        redis: Redis,
    ) -> AsteriskService:
        session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        return AsteriskService(
            session_factory=session_factory,
            redis=redis,
            openai=openai,
            tool_executor=tool_executor,
            stt=stt,
            tts=tts,
            vad=vad,
            converter=converter,
            asterisk=asterisk,
            call_session_manager=call_session_manager,
            host=settings.AUDIOSOCKET_HOST,
            port=settings.AUDIOSOCKET_PORT,
            ai_concurrency=settings.OPENAI_VOICE_CONCURRENCY,
            call_max_duration=settings.CALL_MAX_DURATION,
        )

    @provide(scope=Scope.REQUEST)
    def instagram_svc(
        self, instagram: InstagramClient, orchestrator: ChatOrchestrator, user_repo: UserRepository
    ) -> InstagramService:
        return InstagramService(instagram, orchestrator, user_repo)

    @provide(scope=Scope.REQUEST)
    def telegram_svc(
        self, telegram: TelegramClient, orchestrator: ChatOrchestrator, user_repo: UserRepository
    ) -> TelegramBotService:
        return TelegramBotService(telegram, orchestrator, user_repo)
