import os

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)

files = {}

files["src/clients/crm_client.py"] = """\
from pydantic import BaseModel

from src.clients.base import ABCClient


class LeadDTO(BaseModel):
    phone: str
    name: str | None = None
    channel: str
    order_id: int | None = None


class DealDTO(BaseModel):
    lead_id: str
    product_name: str
    amount: int
    status: str


class CRMClient(ABCClient):
    async def authenticate(self) -> str:
        r = await self.post("/auth/login", json={"login": self._login, "password": self._password})
        return r.data["token"]

    async def create_lead(self, dto: LeadDTO) -> str:
        r = await self.post("/leads", json=dto.model_dump())
        return r.data["id"]

    async def create_deal(self, dto: DealDTO) -> str:
        r = await self.post("/deals", json=dto.model_dump())
        return r.data["id"]

    async def update_contact(self, phone: str, fields: dict) -> None:
        await self.patch(f"/contacts/{phone}", json=fields)

    async def log_call(self, phone: str, duration: int, recording_url: str | None) -> None:
        await self.post("/calls", json={"phone": phone, "duration": duration, "recording": recording_url})
"""

files["src/clients/click_client.py"] = """\
from pydantic import BaseModel

from src.clients.base import ABCClient
from src.core.config import settings


class PaymentLinkDTO(BaseModel):
    payment_id: str
    url: str


class ClickClient(ABCClient):
    async def authenticate(self) -> str:
        return self._password

    async def create_invoice(self, order_id: int, amount: int, phone: str) -> PaymentLinkDTO:
        r = await self.post("/invoice/create", json={
            "service_id": settings.CLICK_SERVICE_ID,
            "merchant_id": settings.CLICK_MERCHANT_ID,
            "amount": amount,
            "transaction_param": str(order_id),
            "phone_number": phone,
        })
        return PaymentLinkDTO(payment_id=r.data["invoice_id"], url=r.data["payment_url"])
"""

files["src/clients/payme_client.py"] = """\
import base64

from src.clients.base import ABCClient
from src.core.config import settings


class PaymeClient(ABCClient):
    async def authenticate(self) -> str:
        return base64.b64encode(
            f"Paycom:{settings.PAYME_SECRET_KEY}".encode()
        ).decode()

    async def create_transaction(self, order_id: int, amount: int) -> dict:
        r = await self.post("/api", json={
            "method": "receipts.create",
            "params": {
                "amount": amount * 100,
                "account": {"order_id": str(order_id)},
            },
        })
        return r.data
"""

files["src/clients/instagram_client.py"] = """\
from src.clients.base import ABCClient
from src.core.config import settings


class InstagramClient(ABCClient):
    async def authenticate(self) -> str:
        return self._password

    async def send_message(self, recipient_id: str, text: str) -> None:
        await self.post(
            f"/{settings.INSTAGRAM_API_VERSION}/me/messages",
            json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            params={"access_token": self._password},
        )
"""

files["src/clients/telegram_client.py"] = """\
from src.clients.base import ABCClient


class TelegramClient(ABCClient):
    async def authenticate(self) -> str:
        return self._password

    async def send_message(self, chat_id: int | str, text: str) -> None:
        token = await self._get_token()
        await self.post(f"/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text})

    async def answer_callback(self, callback_query_id: str) -> None:
        token = await self._get_token()
        await self.post(f"/bot{token}/answerCallbackQuery",
                        json={"callback_query_id": callback_query_id})
"""

files["src/clients/asterisk_client.py"] = """\
import asyncio
import json
from collections.abc import AsyncIterator

import websockets
from pydantic import BaseModel

from src.clients.base import ABCClient


class ChannelDTO(BaseModel):
    id: str
    caller_phone: str
    state: str


class AsteriskEventDTO(BaseModel):
    type: str
    channel_id: str | None = None
    phone: str | None = None
    data: dict = {}


class PlaybackDTO(BaseModel):
    id: str
    state: str


class RecordingDTO(BaseModel):
    name: str
    state: str
    format: str


class AsteriskClient(ABCClient):
    async def authenticate(self) -> str:
        import base64
        return base64.b64encode(f"{self._login}:{self._password}".encode()).decode()

    async def _build_headers(self) -> dict:
        token = await self._get_token()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    async def get_channel(self, channel_id: str) -> ChannelDTO:
        r = await self.get(f"/ari/channels/{channel_id}")
        return ChannelDTO(
            id=r.data["id"],
            caller_phone=r.data["caller"]["number"],
            state=r.data["state"],
        )

    async def answer(self, channel_id: str) -> None:
        await self.post(f"/ari/channels/{channel_id}/answer")

    async def hangup(self, channel_id: str) -> None:
        await self.delete(f"/ari/channels/{channel_id}")

    async def play(self, channel_id: str, media_url: str) -> PlaybackDTO:
        r = await self.post(f"/ari/channels/{channel_id}/play",
                            json={"media": f"sound:{media_url}"})
        return PlaybackDTO(**r.data)

    async def stop_playback(self, playback_id: str) -> None:
        await self.delete(f"/ari/playbacks/{playback_id}")

    async def record(self, channel_id: str, name: str) -> RecordingDTO:
        r = await self.post(f"/ari/channels/{channel_id}/record",
                            json={"name": name, "format": "wav", "beep": False})
        return RecordingDTO(**r.data)

    async def stop_record(self, name: str) -> None:
        await self.post(f"/ari/recordings/live/{name}/stop")

    async def stream_events(self, app: str) -> AsyncIterator[AsteriskEventDTO]:
        ws_url = (
            f"ws://{self._base_url.replace('http://', '').replace('https://', '')}"
            f"/ari/events?api_key={self._login}:{self._password}&app={app}"
        )
        backoff = 1
        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    backoff = 1
                    async for raw in ws:
                        event = json.loads(raw)
                        phone = None
                        if "channel" in event:
                            phone = event["channel"].get("caller", {}).get("number")
                        yield AsteriskEventDTO(
                            type=event.get("type", ""),
                            channel_id=event.get("channel", {}).get("id"),
                            phone=phone,
                            data=event,
                        )
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
"""

files["src/clients/product_api_client.py"] = """\
from pydantic import BaseModel

from src.clients.base import ABCClient


class ProductDTO(BaseModel):
    lot: str
    name_ru: str
    name_uz: str
    description_ru: str
    description_uz: str
    full_price: int
    sale_price: int
    stock: int
    sizes: list[str] = []
    category: str | None = None


class ProductAPIClient(ABCClient):
    async def authenticate(self) -> str:
        r = await self.post("/auth", json={"login": self._login, "password": self._password})
        return r.data["access_token"]

    async def search_by_lot(self, lot: str) -> ProductDTO | None:
        r = await self.get(f"/products/{lot}")
        if not r.ok:
            return None
        return ProductDTO(**r.data)

    async def search(self, query: str, limit: int = 5) -> list[ProductDTO]:
        r = await self.get("/products/search", params={"q": query, "limit": limit})
        return [ProductDTO(**item) for item in r.data.get("items", [])]
"""

files["src/clients/__init__.py"] = """\
from src.clients.asterisk_client import AsteriskClient
from src.clients.base import ABCClient, RequestDTO, ResponseDTO
from src.clients.click_client import ClickClient
from src.clients.crm_client import CRMClient
from src.clients.instagram_client import InstagramClient
from src.clients.openai_client import OpenAIClient
from src.clients.payme_client import PaymeClient
from src.clients.product_api_client import ProductAPIClient
from src.clients.telegram_client import TelegramClient

__all__ = [
    "ABCClient",
    "AsteriskClient",
    "ClickClient",
    "CRMClient",
    "InstagramClient",
    "OpenAIClient",
    "PaymeClient",
    "ProductAPIClient",
    "RequestDTO",
    "ResponseDTO",
    "TelegramClient",
]
"""

for path, content in files.items():
    full_path = os.path.join(PROJECT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    print(f"wrote {path}")
