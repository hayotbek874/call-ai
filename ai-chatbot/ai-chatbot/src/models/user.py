from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)

    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    instagram_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
