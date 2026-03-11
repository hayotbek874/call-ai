import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src.core.config import settings

_SENSITIVE_KEYS = frozenset(
    {
        "phone",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "password_hash",
        "sign_string",
        "signature",
        "callback_query_id",
        "credentials",
    }
)

_PHONE_RE = re.compile(r"(\+?\d{3})\d{5,}(\d{2})")
_TOKEN_RE = re.compile(r"(eyJ[\w-]{5})[\w-]+\.[\w-]+\.[\w-]+([\w-]{4})")

def _mask_value(key: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if key in _SENSITIVE_KEYS:
        if len(value) <= 4:
            return "***"
        return f"{value[:3]}***{value[-2:]}"
    m = _TOKEN_RE.search(value)
    if m:
        return _TOKEN_RE.sub(r"\1***.\2", value)
    return value

def _mask_sensitive(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    for key in list(event_dict):
        if key in _SENSITIVE_KEYS:
            event_dict[key] = _mask_value(key, event_dict[key])
    return event_dict

def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        _mask_sensitive,
    ]

    if settings.LOG_FORMAT == "json":
        processors: list[Processor] = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.AsyncBoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(log_level)
    logging.getLogger("uvicorn.error").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if not settings.DB_ECHO else logging.DEBUG
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    if settings.LOG_FILE_PATH:
        file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
        file_handler.setLevel(log_level)

        if settings.LOG_FORMAT == "json":
            file_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )

        logging.getLogger().addHandler(file_handler)

def get_logger(name: str) -> structlog.stdlib.AsyncBoundLogger:
    return structlog.get_logger(name)

def mask_phone(phone: str | None) -> str:
    if not phone:
        return "none"
    if len(phone) <= 5:
        return "***"
    return f"{phone[:4]}***{phone[-2:]}"

def mask_token(token: str | None) -> str:
    if not token:
        return "none"
    if len(token) <= 8:
        return "***"
    return f"{token[:6]}***{token[-4:]}"

def bind_context(**kwargs: Any) -> None:
    structlog.contextvars.bind_contextvars(**kwargs)

def clear_context() -> None:
    structlog.contextvars.clear_contextvars()

def unbind_context(*keys: str) -> None:
    structlog.contextvars.unbind_contextvars(*keys)
