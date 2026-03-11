from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter
from pydantic import BaseModel

from src.core.logging import get_logger, mask_phone
from src.repositories.user_repository import UserRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

class UserRegisterRequest(BaseModel):
    phone: str
    telegram_id: int | None = None
    instagram_id: str | None = None
    channel: str = "web"
    language: str = "ru"

class UserResponse(BaseModel):
    phone: str
    name: str | None = None
    language: str
    channel: str

@router.post("/register")
@inject
async def register_user(
    body: UserRegisterRequest,
    user_repo: FromDishka[UserRepository],
) -> dict:
    await logger.info("register_user", phone=mask_phone(body.phone), channel=body.channel)
    existing = await user_repo.get_by_phone(body.phone)
    if existing:
        await logger.info("user_already_exists", phone=mask_phone(body.phone))
        return {"status": "exists", "phone": existing.phone}
    user = await user_repo.create(
        phone=body.phone,
        telegram_id=body.telegram_id,
        instagram_id=body.instagram_id,
        channel=body.channel,
        language=body.language,
    )
    await logger.info("user_created", phone=mask_phone(user.phone))
    return {"status": "created", "phone": user.phone}

@router.get("/{phone}")
@inject
async def get_user(
    phone: str,
    user_repo: FromDishka[UserRepository],
) -> UserResponse | dict:
    await logger.info("get_user", phone=mask_phone(phone))
    user = await user_repo.get_by_phone(phone)
    if not user:
        await logger.info("user_not_found", phone=mask_phone(phone))
        return {"error": "not_found"}
    return UserResponse(
        phone=user.phone,
        name=user.name,
        language=user.language,
        channel=user.channel,
    )
