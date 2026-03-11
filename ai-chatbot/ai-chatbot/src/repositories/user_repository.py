from sqlalchemy import select, update

from src.core.logging import get_logger, mask_phone
from src.models.user import User
from src.repositories.base import BaseRepository

logger = get_logger(__name__)

class UserRepository(BaseRepository):
    async def get_by_phone(self, phone: str) -> User | None:
        await logger.debug("user_get_by_phone", phone=mask_phone(phone))
        stmt = select(User).where(User.phone == phone)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        await logger.debug(
            "user_get_by_phone_result", phone=mask_phone(phone), found=user is not None
        )
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        await logger.debug("user_get_by_telegram_id", telegram_id=telegram_id)
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        await logger.debug(
            "user_get_by_telegram_id_result", telegram_id=telegram_id, found=user is not None
        )
        return user

    async def get_by_instagram_id(self, instagram_id: str) -> User | None:
        await logger.debug("user_get_by_instagram_id", instagram_id=instagram_id)
        stmt = select(User).where(User.instagram_id == instagram_id)
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        await logger.debug(
            "user_get_by_instagram_id_result", instagram_id=instagram_id, found=user is not None
        )
        return user

    async def create(self, **kwargs) -> User:
        await logger.info(
            "user_create", phone=mask_phone(kwargs.get("phone")), channel=kwargs.get("channel")
        )
        user = User(**kwargs)
        self._session.add(user)
        await self._session.flush()
        await logger.info(
            "user_created", user_id=user.id, phone=mask_phone(user.phone), channel=user.channel
        )
        return user

    async def update_phone(self, user_id: int, phone: str) -> None:
        await logger.info("user_update_phone", user_id=user_id, phone=mask_phone(phone))
        stmt = update(User).where(User.id == user_id).values(phone=phone)
        await self._session.execute(stmt)
        await self._session.flush()

    async def update_language(self, phone: str, language: str) -> None:
        await logger.info("user_update_language", phone=mask_phone(phone), language=language)
        stmt = update(User).where(User.phone == phone).values(language=language)
        await self._session.execute(stmt)
        await self._session.flush()

    async def update_language_by_telegram_id(self, telegram_id: int, language: str) -> None:
        await logger.info("user_update_language_by_tg", telegram_id=telegram_id, language=language)
        stmt = update(User).where(User.telegram_id == telegram_id).values(language=language)
        await self._session.execute(stmt)
        await self._session.flush()

    async def create_from_telegram(
        self,
        telegram_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        username: str | None = None,
    ) -> User:
        await logger.info("user_create_from_telegram", telegram_id=telegram_id, username=username)
        user = User(
            telegram_id=telegram_id,
            telegram_first_name=first_name,
            telegram_last_name=last_name,
            telegram_username=username,
            name=first_name,
            channel="telegram",
            language="ru",
        )
        self._session.add(user)
        await self._session.flush()
        await logger.info("user_created_from_telegram", user_id=user.id, telegram_id=telegram_id)
        return user

    async def set_phone_by_telegram_id(self, telegram_id: int, phone: str) -> None:
        await logger.info("user_set_phone_by_tg", telegram_id=telegram_id, phone=mask_phone(phone))
        stmt = update(User).where(User.telegram_id == telegram_id).values(phone=phone)
        await self._session.execute(stmt)
        await self._session.flush()
