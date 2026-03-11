from sqlalchemy import desc, select

from src.core.logging import get_logger, mask_phone
from src.models.conversation import ConversationMessage, ConversationSummary
from src.repositories.base import BaseRepository

logger = get_logger(__name__)

class ConversationRepository(BaseRepository):
    async def get_last_messages_by_phone(
        self, phone: str, channel: str | None = None, limit: int = 10,
    ) -> list[ConversationMessage]:
        await logger.debug(
            "get_last_messages", phone=mask_phone(phone), channel=channel, limit=limit,
        )
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.phone == phone)
        )
        if channel is not None:
            stmt = stmt.where(ConversationMessage.channel == channel)
        stmt = stmt.order_by(desc(ConversationMessage.created_at)).limit(limit)
        result = await self._session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()
        await logger.debug("messages_loaded", phone=mask_phone(phone), count=len(messages))
        return messages

    async def save_message_by_phone(
        self,
        phone: str,
        role: str,
        content: str,
        channel: str | None = None,
        intent: str | None = None,
    ) -> ConversationMessage:
        await logger.debug(
            "save_message",
            phone=mask_phone(phone),
            role=role,
            channel=channel,
            intent=intent,
            content_len=len(content),
        )
        msg = ConversationMessage(
            phone=phone, role=role, content=content, channel=channel, intent=intent,
        )
        self._session.add(msg)
        await self._session.flush()
        await logger.debug("message_saved", phone=mask_phone(phone), message_id=msg.id, role=role)
        return msg

    async def get_last_summary(self, phone: str, channel: str | None = None) -> str | None:
        await logger.debug("get_last_summary", phone=mask_phone(phone), channel=channel)
        stmt = (
            select(ConversationSummary.summary)
            .where(ConversationSummary.phone == phone)
        )
        if channel is not None:
            stmt = stmt.where(ConversationSummary.channel == channel)
        stmt = stmt.order_by(desc(ConversationSummary.created_at)).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        await logger.debug("summary_loaded", phone=mask_phone(phone), found=row is not None)
        return row

    async def save_summary(
        self, phone: str, summary: str, channel: str | None = None,
    ) -> ConversationSummary:
        await logger.debug(
            "save_summary", phone=mask_phone(phone), channel=channel, summary_len=len(summary),
        )
        s = ConversationSummary(phone=phone, summary=summary, channel=channel)
        self._session.add(s)
        await self._session.flush()
        await logger.debug("summary_saved", phone=mask_phone(phone), summary_id=s.id)
        return s
