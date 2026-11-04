"""Зависимости FastAPI: авторизация, роли, доступ бота."""

from collections.abc import Callable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import BotRole, UserRole
from app.core.security import TOKEN_ACCESS, decode_token
from app.db.session import get_db
from app.models import BotUser, User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Требуется авторизация",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:  # истёк, подпись неверна и т. п.
        raise CREDENTIALS_ERROR from exc

    if payload.get("type") != TOKEN_ACCESS:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(payload.get("sub", 0))
    except (TypeError, ValueError) as exc:
        raise CREDENTIALS_ERROR from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для этой операции",
            )
        return user

    return checker


def verify_bot_token(x_bot_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_bot_token or x_bot_token != settings.bot_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен бота",
        )


def get_bot_user(db: Session, telegram_id: int) -> BotUser:
    bot_user = db.scalar(select(BotUser).where(BotUser.telegram_id == telegram_id))
    if bot_user is None or not bot_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь бота не найден. Выполните /start.",
        )
    return bot_user


def ensure_manager(bot_user: BotUser) -> None:
    if bot_user.role != BotRole.MANAGER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Действие доступно только менеджеру",
        )


MANAGER_ROLES = (UserRole.ADMIN.value, UserRole.MANAGER.value)
