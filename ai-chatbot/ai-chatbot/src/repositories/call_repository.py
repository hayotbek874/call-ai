from sqlalchemy import select, update

from src.core.logging import get_logger, mask_phone
from src.models.call import Call
from src.models.user import User
from src.repositories.base import BaseRepository

logger = get_logger(__name__)

class CallRepository(BaseRepository):
    async def create(self, phone: str, asterisk_call_id: str) -> Call:
        await logger.info("call_create", phone=mask_phone(phone), asterisk_call_id=asterisk_call_id)
        call = Call(phone=phone, asterisk_call_id=asterisk_call_id)
        self._session.add(call)
        await self._session.flush()
        await logger.info("call_created", call_id=call.id, phone=mask_phone(phone))
        return call

    async def update(self, call_id: int, **kwargs) -> None:
        await logger.info("call_update", call_id=call_id, fields=list(kwargs.keys()))
        stmt = update(Call).where(Call.id == call_id).values(**kwargs)
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_user_language(self, phone: str) -> str | None:
        await logger.debug("get_user_language", phone=mask_phone(phone))
        stmt = select(User.language).where(User.phone == phone)
        result = await self._session.execute(stmt)
        lang = result.scalar_one_or_none()
        await logger.debug("get_user_language_result", phone=mask_phone(phone), language=lang)
        return lang
