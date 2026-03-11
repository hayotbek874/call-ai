from sqlalchemy import select, update

from src.core.logging import get_logger, mask_phone
from src.models.order import Order
from src.repositories.base import BaseRepository

logger = get_logger(__name__)

class OrderRepository(BaseRepository):
    async def create(self, **kwargs) -> Order:
        await logger.debug(
            "order_create",
            phone=mask_phone(kwargs.get("phone")),
            product_lot=kwargs.get("product_lot"),
        )
        order = Order(**kwargs)
        self._session.add(order)
        await self._session.flush()
        await logger.debug(
            "order_created", order_id=order.id, phone=mask_phone(order.phone), status=order.status
        )
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        await logger.debug("order_get_by_id", order_id=order_id)
        stmt = select(Order).where(Order.id == order_id)
        result = await self._session.execute(stmt)
        order = result.scalar_one_or_none()
        await logger.debug("order_get_by_id_result", order_id=order_id, found=order is not None)
        return order

    async def get_by_phone(self, phone: str, limit: int = 10) -> list[Order]:
        await logger.debug("order_get_by_phone", phone=mask_phone(phone), limit=limit)
        stmt = (
            select(Order).where(Order.phone == phone).order_by(Order.created_at.desc()).limit(limit)
        )
        result = await self._session.execute(stmt)
        orders = list(result.scalars().all())
        await logger.debug("orders_loaded", phone=mask_phone(phone), count=len(orders))
        return orders

    async def update_status(self, order_id: int, status: str) -> None:
        await logger.info("order_update_status", order_id=order_id, new_status=status)
        stmt = update(Order).where(Order.id == order_id).values(status=status)
        await self._session.execute(stmt)
        await self._session.flush()
