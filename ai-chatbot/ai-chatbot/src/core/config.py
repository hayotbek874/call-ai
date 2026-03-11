from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class ProjectSettings(BaseSettings):
    APP_NAME: str = "stratix-ai-chatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "prod"

class ServerSettings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = ["*"]

class DatabaseSettings(BaseSettings):
    POSTGRES_URL: str = "postgresql+asyncpg://stratix:stratix@postgres:5432/stratix"
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20

class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_TTL: int = 3600

class AISettings(BaseSettings):

    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-2.5-pro"
    GEMINI_AUDIO_MODEL: str = "gemini-2.5-flash-native-audio-latest"
    GEMINI_VOICE_RU: str = "Kore"
    GEMINI_VOICE_UZ: str = "Kore"

    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_STT_MODEL: str = "whisper-1"
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE_RU: str = "onyx"
    OPENAI_TTS_VOICE_UZ: str = "onyx"

class AsteriskSettings(BaseSettings):
    ASTERISK_HOST: str = "127.0.0.1"
    ASTERISK_PORT: int = 8088
    ASTERISK_ARI_USER: str = "asterisk"
    ASTERISK_ARI_PASSWORD: str = "asterisk"
    ASTERISK_ARI_APP: str = "stratix"
    ASTERISK_IP_WHITELIST: list[str] = ["127.0.0.1"]

class TelegramSettings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

class InstagramSettings(BaseSettings):
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_VERIFY_TOKEN: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_API_VERSION: str = "v19.0"

class PaymentSettings(BaseSettings):
    CLICK_SERVICE_ID: str = ""
    CLICK_MERCHANT_ID: str = ""
    CLICK_SECRET_KEY: str = ""
    PAYME_MERCHANT_ID: str = ""
    PAYME_SECRET_KEY: str = ""

class CRMSettings(BaseSettings):
    CRM_BASE_URL: str = ""
    CRM_API_KEY: str = ""

class JWTSettings(BaseSettings):
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 30

class VoiceSettings(BaseSettings):
    AUDIOSOCKET_HOST: str = "0.0.0.0"
    AUDIOSOCKET_PORT: int = 9099
    MAX_CONCURRENT_CALLS: int = 20
    OPENAI_VOICE_CONCURRENCY: int = 5
    CALL_MAX_DURATION: int = 600
    SILENCE_TIMEOUT_SECONDS: int = 30

class CelerySettings(BaseSettings):
    CELERY_BROKER_URL: str = "amqp://guest:guest@rabbitmq:5672//"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

class LoggingSettings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: str = ""
    DB_ECHO: bool = False

class Settings(
    ProjectSettings,
    ServerSettings,
    DatabaseSettings,
    RedisSettings,
    AISettings,
    AsteriskSettings,
    TelegramSettings,
    InstagramSettings,
    PaymentSettings,
    CRMSettings,
    JWTSettings,
    VoiceSettings,
    CelerySettings,
    LoggingSettings,
):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
