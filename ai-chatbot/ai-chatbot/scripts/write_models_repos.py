import os

PROJECT = "/Users/shaxzodbek/PycharmProjects/STRATIX_AI_CHAT_BOT"
files = {}

# ============================================================
# MODELS
# ============================================================

files["src/models/user.py"] = """\
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    instagram_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
"""

files["src/models/conversation.py"] = """\
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
"""

files["src/models/call.py"] = """\
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
"""

files["src/models/order.py"] = """\
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
"""

files["src/models/__init__.py"] = """\
from src.models.call import Call
from src.models.clients_tokens import ClientToken, ClientsTokens, ClientType
from src.models.conversation import ConversationMessage, ConversationSummary
from src.models.order import Order
from src.models.user import User

__all__ = [
    "Call",
    "ClientToken",
    "ClientsTokens",
    "ClientType",
    "ConversationMessage",
    "ConversationSummary",
    "Order",
    "User",
]
"""

# ============================================================
# REPOSITORIES
# ============================================================

files["src/repositories/base.py"] = """\
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self._session = session
"""

files["src/repositories/user_repository.py"] = """\
from sqlalchemy import select, update

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_phone(self, phone: str) -> User | None:
        stmt = select(User).where(User.phone == phone)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_instagram_id(self, instagram_id: str) -> User | None:
        stmt = select(User).where(User.instagram_id == instagram_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_phone(self, user_id: int, phone: str) -> None:
        stmt = update(User).where(User.id == user_id).values(phone=phone)
        await self._session.execute(stmt)
        await self._session.flush()

    async def update_language(self, phone: str, language: str) -> None:
        stmt = update(User).where(User.phone == phone).values(language=language)
        await self._session.execute(stmt)
        await self._session.flush()
"""

files["src/repositories/conversation_repository.py"] = """\
from sqlalchemy import desc, select

from src.models.conversation import ConversationMessage, ConversationSummary
from src.repositories.base import BaseRepository


class ConversationRepository(BaseRepository):
    async def get_last_messages_by_phone(self, phone: str, limit: int = 10) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.phone == phone)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def save_message_by_phone(self, phone: str, role: str, content: str,
                                     intent: str | None = None) -> ConversationMessage:
        msg = ConversationMessage(phone=phone, role=role, content=content, intent=intent)
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_last_summary(self, phone: str) -> str | None:
        stmt = (
            select(ConversationSummary.summary)
            .where(ConversationSummary.phone == phone)
            .order_by(desc(ConversationSummary.created_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def save_summary(self, phone: str, summary: str) -> ConversationSummary:
        s = ConversationSummary(phone=phone, summary=summary)
        self._session.add(s)
        await self._session.flush()
        return s
"""

files["src/repositories/call_repository.py"] = """\
from sqlalchemy import select, update

from src.models.call import Call
from src.models.user import User
from src.repositories.base import BaseRepository


class CallRepository(BaseRepository):
    async def create(self, phone: str, asterisk_call_id: str) -> Call:
        call = Call(phone=phone, asterisk_call_id=asterisk_call_id)
        self._session.add(call)
        await self._session.flush()
        return call

    async def update(self, call_id: int, **kwargs) -> None:
        stmt = update(Call).where(Call.id == call_id).values(**kwargs)
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_user_language(self, phone: str) -> str | None:
        stmt = select(User.language).where(User.phone == phone)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
"""

files["src/repositories/order_repository.py"] = """\
from sqlalchemy import select, update

from src.models.order import Order
from src.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    async def create(self, **kwargs) -> Order:
        order = Order(**kwargs)
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str, limit: int = 10) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.phone == phone)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, order_id: int, status: str) -> None:
        stmt = update(Order).where(Order.id == order_id).values(status=status)
        await self._session.execute(stmt)
        await self._session.flush()
"""

files["src/repositories/__init__.py"] = """\
from src.repositories.call_repository import CallRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.order_repository import OrderRepository
from src.repositories.user_repository import UserRepository

__all__ = [
    "CallRepository",
    "ConversationRepository",
    "OrderRepository",
    "UserRepository",
]
"""

for path, content in files.items():
    full_path = os.path.join(PROJECT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    print(f"wrote {path}")
