import asyncio
import functools
import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any, ParamSpec, TypeVar

from redis.asyncio import Redis

from src.core.logging import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
        retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504),
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions
        self.retryable_status_codes = retryable_status_codes

def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        await logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    delay = min(
                        initial_delay * (exponential_base**attempt),
                        max_delay,
                    )
                    await logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)

            if last_exception:
                raise last_exception

            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator

def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    key_parts = [prefix, func_name]
    serializable_args = []
    for arg in args:
        if hasattr(arg, "__dict__") and not isinstance(arg, (str, int, float, bool, list, dict)):
            continue
        serializable_args.append(arg)

    if serializable_args:
        args_str = json.dumps(serializable_args, sort_keys=True, default=str)
        key_parts.append(hashlib.md5(args_str.encode()).hexdigest()[:8])

    if kwargs:
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])

    return ":".join(key_parts)

def cache(
    prefix: str = "cache",
    ttl: int | timedelta = 300,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    ttl_seconds = int(ttl.total_seconds()) if isinstance(ttl, timedelta) else ttl

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            redis_client: Redis | None = kwargs.pop("_redis", None)

            if redis_client is None and args:
                first_arg = args[0]
                if hasattr(first_arg, "_redis"):
                    redis_client = first_arg._redis

            if redis_client is None:
                await logger.debug(f"No Redis client available for caching {func.__name__}")
                return await func(*args, **kwargs)

            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(prefix, func.__name__, args, kwargs)

            try:
                cached_value = await redis_client.get(cache_key)
                if cached_value is not None:
                    await logger.debug(f"Cache hit for {cache_key}")
                    return json.loads(cached_value)
            except Exception as e:
                await logger.warning(f"Cache read error for {cache_key}: {e}")

            result = await func(*args, **kwargs)

            try:
                await redis_client.setex(cache_key, ttl_seconds, json.dumps(result, default=str))
                await logger.debug(f"Cached result for {cache_key} with TTL {ttl_seconds}s")
            except Exception as e:
                await logger.warning(f"Cache write error for {cache_key}: {e}")

            return result

        return wrapper

    return decorator

def invalidate_cache(redis_client: Redis, pattern: str) -> Callable[..., Any]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = await func(*args, **kwargs)
            try:
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
                    await logger.debug(f"Invalidated {len(keys)} cache entries matching {pattern}")
            except Exception as e:
                await logger.warning(f"Cache invalidation error for pattern {pattern}: {e}")

            return result

        return wrapper

    return decorator

class CacheManager:
    def __init__(self, redis: Redis, default_ttl: int = 300) -> None:
        self._redis = redis
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            await logger.warning(f"Cache get error for {key}: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            ttl = ttl or self._default_ttl
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            await logger.warning(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            await logger.warning(f"Cache delete error for {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
                return len(keys)
        except Exception as e:
            await logger.warning(f"Cache invalidation error for pattern {pattern}: {e}")
        return 0

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            await logger.warning(f"Cache exists error for {key}: {e}")
            return False
