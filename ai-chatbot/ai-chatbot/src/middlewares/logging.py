import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)

_SKIP_LOG_PATHS = {"/api/v1/health"}

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_LOG_PATHS:
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        bind_context(request_id=request_id)
        start = time.perf_counter()
        await logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
            client_ip=request.client.host if request.client else "unknown",
        )
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            await logger.info(
                "request_finished",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            await logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise
        finally:
            clear_context()
