from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.security import decode_access_token

_bearer = HTTPBearer()

async def get_current_admin_id(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> int:
    payload = decode_access_token(creds.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
