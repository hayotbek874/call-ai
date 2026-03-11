from sqlalchemy import func, select

from src.core.logging import get_logger
from src.models.admin import Admin
from src.repositories.base import BaseRepository

logger = get_logger(__name__)

class AdminRepository(BaseRepository):
    async def get_by_username(self, username: str) -> Admin | None:
        await logger.debug("admin_get_by_username", username=username)
        stmt = select(Admin).where(Admin.username == username, Admin.is_active.is_(True))
        result = await self._session.execute(stmt)
        admin = result.scalar_one_or_none()
        await logger.debug(
            "admin_get_by_username_result", username=username, found=admin is not None
        )
        return admin

    async def get_by_id(self, admin_id: int) -> Admin | None:
        await logger.debug("admin_get_by_id", admin_id=admin_id)
        stmt = select(Admin).where(Admin.id == admin_id, Admin.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, username: str, password_hash: str) -> Admin:
        await logger.info("admin_create", username=username)
        admin = Admin(username=username, password_hash=password_hash)
        self._session.add(admin)
        await self._session.flush()
        await logger.info("admin_created", admin_id=admin.id, username=admin.username)
        return admin

    async def count(self) -> int:
        result = await self._session.execute(select(func.count(Admin.id)))
        return result.scalar_one()
