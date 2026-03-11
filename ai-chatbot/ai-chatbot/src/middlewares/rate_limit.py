from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging import get_logger

logger = get_logger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis=None, public_limit: int = 60, auth_limit: int = 300):
        super().__init__(app)
        self._redis = redis
        self._public_limit = public_limit
        self._auth_limit = auth_limit

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._redis is None:
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        user = getattr(request.state, "user", None)
        if user:
            key = f"rate:{user.get('sub', client_ip)}"
            limit = self._auth_limit
        else:
            key = f"rate:{client_ip}"
            limit = self._public_limit
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 60)
        if count > limit:
            await logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                count=count,
                limit=limit,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
            )
        return await call_next(request)
