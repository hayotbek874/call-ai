import base64

from src.clients.base import ABCClient
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class PaymeClient(ABCClient):
    async def authenticate(self) -> str:
        return base64.b64encode(f"Paycom:{settings.PAYME_SECRET_KEY}".encode()).decode()

    async def create_transaction(self, order_id: int, amount: int) -> dict:
        await logger.info("payme_create_transaction", order_id=order_id, amount=amount)
        r = await self.post(
            "/api",
            json={
                "method": "receipts.create",
                "params": {
                    "amount": amount * 100,
                    "account": {"order_id": str(order_id)},
                },
            },
        )
        await logger.info("payme_transaction_created", order_id=order_id)
        return r.data
