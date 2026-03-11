from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin import Admin
from src.models.call import Call
from src.models.conversation import ConversationMessage
from src.models.order import Order
from src.models.user import User
from src.schemas.statistics import (
    AdminStats,
    CallStats,
    ConversationStats,
    DashboardStats,
    OrderStats,
    UserStats,
)

class StatisticsService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def collect(self) -> dict:
        users = await self._user_stats()
        orders = await self._order_stats()
        conversations = await self._conversation_stats()
        calls = await self._call_stats()
        admins = await self._admin_stats()
        dashboard = DashboardStats(
            users=users,
            orders=orders,
            conversations=conversations,
            calls=calls,
            admins=admins,
            collected_at=datetime.now(UTC).isoformat(),
        )
        return asdict(dashboard)

    async def _user_stats(self) -> UserStats:
        today = datetime.now(UTC).date()
        total_q = select(func.count(User.id))
        active_q = select(func.count(User.id)).where(User.is_active.is_(True))
        today_q = select(func.count(User.id)).where(func.date(User.created_at) == today)
        channel_q = select(User.channel, func.count(User.id)).group_by(User.channel)

        total = (await self._session.execute(total_q)).scalar_one()
        active = (await self._session.execute(active_q)).scalar_one()
        today_new = (await self._session.execute(today_q)).scalar_one()
        rows = (await self._session.execute(channel_q)).all()
        by_channel = {r[0]: r[1] for r in rows}
        return UserStats(total=total, active=active, by_channel=by_channel, today_new=today_new)

    async def _order_stats(self) -> OrderStats:
        today = datetime.now(UTC).date()
        total_q = select(func.count(Order.id))
        pending_q = select(func.count(Order.id)).where(Order.status == "pending")
        completed_q = select(func.count(Order.id)).where(Order.status == "completed")
        cancelled_q = select(func.count(Order.id)).where(Order.status == "cancelled")
        today_q = select(func.count(Order.id)).where(func.date(Order.created_at) == today)
        today_rev_q = select(func.coalesce(func.sum(Order.total), 0)).where(
            func.date(Order.created_at) == today
        )
        status_q = select(Order.status, func.count(Order.id)).group_by(Order.status)
        channel_q = select(Order.channel, func.count(Order.id)).group_by(Order.channel)

        total = (await self._session.execute(total_q)).scalar_one()
        pending = (await self._session.execute(pending_q)).scalar_one()
        completed = (await self._session.execute(completed_q)).scalar_one()
        cancelled = (await self._session.execute(cancelled_q)).scalar_one()
        today_total = (await self._session.execute(today_q)).scalar_one()
        today_revenue = (await self._session.execute(today_rev_q)).scalar_one()
        by_status = {r[0]: r[1] for r in (await self._session.execute(status_q)).all()}
        by_channel = {r[0]: r[1] for r in (await self._session.execute(channel_q)).all()}
        return OrderStats(
            total=total,
            pending=pending,
            completed=completed,
            cancelled=cancelled,
            today_total=today_total,
            today_revenue=today_revenue,
            by_status=by_status,
            by_channel=by_channel,
        )

    async def _conversation_stats(self) -> ConversationStats:
        today = datetime.now(UTC).date()
        total_q = select(func.count(ConversationMessage.id))
        today_q = select(func.count(ConversationMessage.id)).where(
            func.date(ConversationMessage.created_at) == today
        )
        role_q = select(ConversationMessage.role, func.count(ConversationMessage.id)).group_by(
            ConversationMessage.role
        )
        channel_q = select(
            ConversationMessage.channel, func.count(ConversationMessage.id)
        ).group_by(ConversationMessage.channel)

        total = (await self._session.execute(total_q)).scalar_one()
        today_msgs = (await self._session.execute(today_q)).scalar_one()
        by_role = {r[0]: r[1] for r in (await self._session.execute(role_q)).all()}
        by_channel = {
            (r[0] or "unknown"): r[1] for r in (await self._session.execute(channel_q)).all()
        }
        return ConversationStats(
            total_messages=total,
            today_messages=today_msgs,
            by_role=by_role,
            by_channel=by_channel,
        )

    async def _call_stats(self) -> CallStats:
        today = datetime.now(UTC).date()
        total_q = select(func.count(Call.id))
        today_q = select(func.count(Call.id)).where(func.date(Call.created_at) == today)
        status_q = select(Call.status, func.count(Call.id)).group_by(Call.status)
        avg_q = select(func.coalesce(func.avg(Call.duration), 0))

        total = (await self._session.execute(total_q)).scalar_one()
        today_total = (await self._session.execute(today_q)).scalar_one()
        by_status = {r[0]: r[1] for r in (await self._session.execute(status_q)).all()}
        avg_duration = float((await self._session.execute(avg_q)).scalar_one())
        return CallStats(
            total=total, today_total=today_total, by_status=by_status, avg_duration=avg_duration
        )

    async def _admin_stats(self) -> AdminStats:
        result = await self._session.execute(select(func.count(Admin.id)))
        return AdminStats(total_admins=result.scalar_one())
