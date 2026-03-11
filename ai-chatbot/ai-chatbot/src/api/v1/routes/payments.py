from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.clients.click_client import ClickClient
from src.clients.payme_client import PaymeClient
from src.core.logging import get_logger, mask_phone
from src.repositories.order_repository import OrderRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentCreateRequest(BaseModel):
    order_id: int
    amount: int
    phone: str
    method: str = "click"

@router.post("/create")
@inject
async def create_payment(
    body: PaymentCreateRequest,
    click_client: FromDishka[ClickClient],
    payme_client: FromDishka[PaymeClient],
    order_repo: FromDishka[OrderRepository],
) -> dict:
    await logger.info(
        "create_payment",
        order_id=body.order_id,
        amount=body.amount,
        method=body.method,
        phone=mask_phone(body.phone),
    )
    if body.method == "click":
        result = await click_client.create_invoice(body.order_id, body.amount, body.phone)
        await logger.info("payment_created", method="click", payment_id=result.payment_id)
        return {"payment_id": result.payment_id, "url": result.url}
    elif body.method == "payme":
        result = await payme_client.create_transaction(body.order_id, body.amount)
        await logger.info("payment_created", method="payme", order_id=body.order_id)
        return result
    await logger.warning("unsupported_payment_method", method=body.method)
    return {"error": "unsupported_method"}

@router.post("/click/callback")
@inject
async def click_callback(
    request: Request,
    order_repo: FromDishka[OrderRepository],
) -> dict:
    body = await request.json()
    body.get("sign_string", "")
    order_id = int(body.get("merchant_trans_id", 0))
    await logger.info("click_callback", order_id=order_id)
    if order_id:
        await order_repo.update_status(order_id, "paid")
        await logger.info("order_paid", order_id=order_id, provider="click")
    return {"error": 0, "error_note": "Success"}

@router.post("/payme/callback")
@inject
async def payme_callback(
    request: Request,
    order_repo: FromDishka[OrderRepository],
) -> dict:
    body = await request.json()
    method = body.get("method", "")
    params = body.get("params", {})
    await logger.info("payme_callback", method=method)
    if method == "PerformTransaction":
        account = params.get("account", {})
        order_id = int(account.get("order_id", 0))
        if order_id:
            await order_repo.update_status(order_id, "paid")
            await logger.info("order_paid", order_id=order_id, provider="payme")
    return {"result": {"allow": True}}
