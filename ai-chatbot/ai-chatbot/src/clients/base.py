import asyncio
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel
from redis.asyncio import Redis

from src.core.logging import get_logger

logger = get_logger(__name__)

class RequestDTO(BaseModel):
    method: str
    path: str
    body: dict | None = None
    params: dict | None = None
    headers: dict | None = None

class ResponseDTO(BaseModel):
    status_code: int
    data: dict | list | str | None
    headers: dict

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

class ABCClient(ABC):
    def __init__(self, base_url: str, login: str, password: str, redis: Redis, client_name: str):
        self._base_url = base_url
        self._login = login
        self._password = password
        self._redis = redis
        self._client_name = client_name
        self._token_key = f"token:{client_name}"

    @abstractmethod
    async def authenticate(self) -> str: ...

    async def _get_token(self) -> str:
        cached = await self._redis.get(self._token_key)
        if cached:
            return cached if isinstance(cached, str) else cached.decode()
        token = await self.authenticate()
        await self._redis.setex(self._token_key, 3500, token)
        return token

    async def _build_headers(self) -> dict:
        token = await self._get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, **kwargs) -> ResponseDTO:
        headers = await self._build_headers()
        headers.update(kwargs.pop("headers", {}) or {})
        url = f"{self._base_url}{path}"
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    await logger.info(
                        "http_request",
                        client=self._client_name,
                        method=method,
                        path=path,
                        attempt=attempt + 1,
                    )
                    r = await client.request(method, url, headers=headers, **kwargs)
                    if r.status_code >= 500 and attempt < 2:
                        await logger.warning(
                            "http_server_error",
                            client=self._client_name,
                            method=method,
                            path=path,
                            status_code=r.status_code,
                            attempt=attempt + 1,
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    try:
                        data = r.json()
                    except Exception:
                        data = r.text
                    log_fn = logger.info if 200 <= r.status_code < 300 else logger.warning
                    await log_fn(
                        "http_response",
                        client=self._client_name,
                        method=method,
                        path=path,
                        status_code=r.status_code,
                        **({"response_body": data} if r.status_code >= 400 else {}),
                    )
                    return ResponseDTO(
                        status_code=r.status_code, data=data, headers=dict(r.headers)
                    )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                await logger.error(
                    "http_connection_error",
                    client=self._client_name,
                    method=method,
                    path=path,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))
        raise httpx.ConnectError("Max retries exceeded")

    async def get(self, path: str, **kwargs) -> ResponseDTO:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> ResponseDTO:
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> ResponseDTO:
        return await self._request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> ResponseDTO:
        return await self._request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> ResponseDTO:
        return await self._request("DELETE", path, **kwargs)
