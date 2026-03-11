from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter
from pydantic import BaseModel

from src.core.logging import get_logger, mask_phone
from src.repositories.order_repository import OrderRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderCreateRequest(BaseModel):
    phone: str
    product_lot: str
    product_name: str
    quantity: int = 1
    size: str | None = None
    amount: int
    delivery_cost: int = 0
    total: int
    channel: str
    address: str | None = None
    payment_method: str = "cash"

class OrderResponse(BaseModel):
    id: int
    phone: str
    product_lot: str
    product_name: str
    quantity: int
    amount: int
    total: int
    status: str
    channel: str

@router.post("/")
@inject
async def create_order(
    body: OrderCreateRequest,
    order_repo: FromDishka[OrderRepository],
) -> OrderResponse:
    await logger.info(
        "create_order",
        phone=mask_phone(body.phone),
        product_lot=body.product_lot,
        total=body.total,
        channel=body.channel,
    )
    order = await order_repo.create(**body.model_dump())
    await logger.info("order_created", order_id=order.id, phone=mask_phone(body.phone))
    return OrderResponse(
        id=order.id,
        phone=order.phone,
        product_lot=order.product_lot,
        product_name=order.product_name,
        quantity=order.quantity,
        amount=order.amount,
        total=order.total,
        status=order.status,
        channel=order.channel,
    )

@router.get("/{phone}")
@inject
async def get_orders_by_phone(
    phone: str,
    order_repo: FromDishka[OrderRepository],
) -> list[OrderResponse]:
    await logger.info("get_orders_by_phone", phone=mask_phone(phone))
    orders = await order_repo.get_by_phone(phone)
    await logger.info("orders_fetched", phone=mask_phone(phone), count=len(orders))
    return [
        OrderResponse(
            id=o.id,
            phone=o.phone,
            product_lot=o.product_lot,
            product_name=o.product_name,
            quantity=o.quantity,
            amount=o.amount,
            total=o.total,
            status=o.status,
            channel=o.channel,
        )
        for o in orders
    ]
