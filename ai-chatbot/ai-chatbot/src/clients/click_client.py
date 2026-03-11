from pydantic import BaseModel

from src.clients.base import ABCClient
from src.core.config import settings
from src.core.logging import get_logger, mask_phone

logger = get_logger(__name__)

class PaymentLinkDTO(BaseModel):
    payment_id: str
    url: str

class ClickClient(ABCClient):
    async def authenticate(self) -> str:
        return self._password

    async def create_invoice(self, order_id: int, amount: int, phone: str) -> PaymentLinkDTO:
        await logger.info(
            "click_create_invoice", order_id=order_id, amount=amount, phone=mask_phone(phone)
        )
        r = await self.post(
            "/invoice/create",
            json={
                "service_id": settings.CLICK_SERVICE_ID,
                "merchant_id": settings.CLICK_MERCHANT_ID,
                "amount": amount,
                "transaction_param": str(order_id),
                "phone_number": phone,
            },
        )
        await logger.info("click_invoice_created", payment_id=r.data["invoice_id"])
        return PaymentLinkDTO(payment_id=r.data["invoice_id"], url=r.data["payment_url"])
