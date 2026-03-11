import redis.asyncio as aioredis

from src.core.config import settings

async def create_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL)
