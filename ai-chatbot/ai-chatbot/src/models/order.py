from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin

class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    product_lot: Mapped[str] = mapped_column(String(20), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(20), default="cash", nullable=False)
    crm_lead_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
