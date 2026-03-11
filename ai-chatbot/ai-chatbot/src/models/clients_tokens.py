from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin

class ClientType(StrEnum):
    CRM = "crm"

class ClientToken(Base, TimestampMixin):
    __tablename__ = "client_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_type: Mapped[ClientType] = mapped_column(
        Enum(ClientType, native_enum=False),
        nullable=False,
        index=True,
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_type: Mapped[str] = mapped_column(String(50), default="Bearer", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_client_tokens_client_type_expires_at", "client_type", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at

    @property
    def time_until_expiry(self) -> float:
        return (self.expires_at - datetime.now(UTC)).total_seconds()

    def is_expiring_soon(self, buffer_seconds: int = 300) -> bool:
        return self.time_until_expiry <= buffer_seconds

    def __repr__(self) -> str:
        return (
            f"<ClientToken(id={self.id}, client_type={self.client_type}, "
            f"expires_at={self.expires_at}, is_expired={self.is_expired})>"
        )

ClientsTokens = ClientToken
