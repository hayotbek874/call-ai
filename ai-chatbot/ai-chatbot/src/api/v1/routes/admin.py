from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
@inject
async def admin_login(
    body: LoginRequest,
    admin_svc: FromDishka[AdminService],
) -> TokenResponse:
    token = await admin_svc.login(body.username, body.password)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    return TokenResponse(access_token=token)
