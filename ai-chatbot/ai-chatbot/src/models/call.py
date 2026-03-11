from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin

class Call(Base, TimestampMixin):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    asterisk_call_id: Mapped[str] = mapped_column(String(100), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ringing", nullable=False)
    recording_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)
