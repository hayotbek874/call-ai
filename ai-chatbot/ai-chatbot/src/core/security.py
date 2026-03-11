from base64 import b64decode, b64encode
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac
from os import urandom

import jwt

from src.core.config import settings

_ITERATIONS = 600_000
_HASH_NAME = "sha256"
_SALT_LEN = 32

def hash_password(password: str) -> str:
    salt = urandom(_SALT_LEN)
    dk = pbkdf2_hmac(_HASH_NAME, password.encode(), salt, _ITERATIONS)
    return f"{b64encode(salt).decode()}${b64encode(dk).decode()}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_b64, dk_b64 = password_hash.split("$", 1)
        salt = b64decode(salt_b64)
        expected = b64decode(dk_b64)
        dk = pbkdf2_hmac(_HASH_NAME, password.encode(), salt, _ITERATIONS)
        return dk == expected
    except Exception:
        return False

def create_access_token(subject: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
