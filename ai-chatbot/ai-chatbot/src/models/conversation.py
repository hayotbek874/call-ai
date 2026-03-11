from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin

class ConversationMessage(Base, TimestampMixin):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)

class ConversationSummary(Base, TimestampMixin):
    __tablename__ = "conversation_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
