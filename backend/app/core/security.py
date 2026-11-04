"""Хеширование паролей и JWT-токены."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()

TOKEN_ACCESS = "access"
TOKEN_MAGIC = "magic"
TOKEN_CLIENT = "client"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hash.verify(password, hashed)
    except Exception:  # noqa: BLE001 - повреждённый хеш не должен ломать вход
        return False


def _create_token(subject: str, token_type: str, expires_minutes: int, **extra: Any) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        **extra,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: int, role: str) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id),
        TOKEN_ACCESS,
        settings.access_token_expire_minutes,
        role=role,
    )


def create_magic_token(user_id: int) -> str:
    settings = get_settings()
    return _create_token(
        str(user_id),
        TOKEN_MAGIC,
        settings.magic_link_expire_minutes,
    )


def create_client_token(client_id: int) -> str:
    settings = get_settings()
    return _create_token(
        str(client_id),
        TOKEN_CLIENT,
        settings.client_link_expire_minutes,
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
