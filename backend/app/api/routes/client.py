"""Публичный личный кабинет клиента."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import ClientPortalOut
from app.services.client_portal import InvalidClientLink, client_portal

router = APIRouter(prefix="/client", tags=["client"])


@router.get("/portal", response_model=ClientPortalOut)
def portal(
    token: str = Query(min_length=10),
    db: Session = Depends(get_db),
) -> ClientPortalOut:
    """Кабинет клиента: только его заявки и документы.

    Доступ даёт подписанная ссылка из VK/Telegram-бота; пароль не нужен.
    """
    try:
        return client_portal(db, token)
    except InvalidClientLink as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
