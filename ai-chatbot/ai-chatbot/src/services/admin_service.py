from src.core.logging import get_logger
from src.core.security import create_access_token, verify_password
from src.repositories.admin_repository import AdminRepository

logger = get_logger(__name__)

class AdminService:
    def __init__(self, repo: AdminRepository):
        self._repo = repo

    async def login(self, username: str, password: str) -> str | None:
        await logger.info("admin_login_attempt", username=username)
        admin = await self._repo.get_by_username(username)
        if not admin or not verify_password(password, admin.password_hash):
            await logger.warning(
                "admin_login_failed", username=username, reason="invalid_credentials"
            )
            return None
        token = create_access_token(admin.id)
        await logger.info("admin_login_success", username=username, admin_id=admin.id)
        return token
