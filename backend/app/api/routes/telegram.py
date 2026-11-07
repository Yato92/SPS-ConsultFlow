"""Просмотр Telegram-пользователей и очереди уведомлений в дашборде."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import BotUser, Client, Notification, Order, User
from app.schemas import BotUserRow, NotificationOut

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/users", response_model=list[BotUserRow])
def list_bot_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[BotUserRow]:
    users = list(db.scalars(select(BotUser).order_by(BotUser.created_at.desc())).all())

    counts = dict(
        db.execute(
            select(Client.telegram_id, func.count(Order.id))
            .join(Order, Order.client_id == Client.id)
            .where(Client.telegram_id.is_not(None), Order.is_deleted.is_(False))
            .group_by(Client.telegram_id)
        ).all()
    )

    return [
        BotUserRow(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            user_id=user.user_id,
            created_at=user.created_at,
            orders_count=int(counts.get(user.telegram_id, 0)),
        )
        for user in users
    ]


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[NotificationOut]:
    items = db.scalars(
        select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    ).all()
    return [NotificationOut.model_validate(item) for item in items]
