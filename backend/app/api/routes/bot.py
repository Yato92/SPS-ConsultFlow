"""API для Telegram-бота ConsultFlow."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import ensure_manager, get_bot_user, verify_bot_token
from app.core.config import get_settings
from app.core.enums import (
    ACTIVE_STATUSES,
    PRACTICE_LABELS,
    STATUS_LABELS,
    ActorType,
    BotRole,
    OrderStatus,
    UserRole,
)
from app.core.security import create_magic_token
from app.core.utils import utcnow
from app.db.session import get_db
from app.models import BotUser, Client, Notification, Order, User
from app.schemas import (
    BotAIIntakeIn,
    BotAIIntakeOut,
    BotEstimateOut,
    BotLinkOut,
    BotOrderDetailOut,
    BotOrderIn,
    BotOrderOut,
    BotOrderShort,
    BotRegisterOut,
    BotStatsOut,
    BotStatusIn,
    BotUserIn,
    BotUserOut,
    NotificationAckIn,
    NotificationOut,
    OrderEventOut,
)
from app.services.ai_intake import analyze_intake
from app.services.analytics import build_dashboard
from app.services.documents import create_ai_proposal
from app.services.orders import change_status, create_order
from app.services.pricing import estimate, pricing_info

router = APIRouter(
    prefix="/bot",
    tags=["bot"],
    dependencies=[Depends(verify_bot_token)],
)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "consultflow-bot-api", "time": utcnow()}


@router.post("/users", response_model=BotRegisterOut)
def register_user(payload: BotUserIn, db: Session = Depends(get_db)) -> BotRegisterOut:
    settings = get_settings()
    bot_user = db.scalar(
        select(BotUser).where(BotUser.telegram_id == payload.telegram_id)
    )
    if bot_user is None:
        bot_user = BotUser(telegram_id=payload.telegram_id)
        db.add(bot_user)

    bot_user.username = payload.username
    bot_user.full_name = payload.full_name or bot_user.full_name or "Пользователь Telegram"
    if payload.phone:
        bot_user.phone = payload.phone
    if payload.email:
        bot_user.email = payload.email

    is_manager = payload.telegram_id in settings.manager_ids
    if bot_user.role == BotRole.MANAGER.value:
        is_manager = True

    if is_manager:
        bot_user.role = BotRole.MANAGER.value
        if bot_user.user_id is None:
            staff = db.scalar(
                select(User).where(
                    User.is_active.is_(True),
                    User.role.in_([UserRole.MANAGER.value, UserRole.ADMIN.value]),
                )
            )
            if staff is not None:
                bot_user.user_id = staff.id

    db.commit()
    db.refresh(bot_user)
    manager_name = None
    if bot_user.user_id:
        manager = db.get(User, bot_user.user_id)
        manager_name = manager.full_name if manager else None

    return BotRegisterOut(
        user=BotUserOut.model_validate(bot_user),
        is_manager=is_manager,
        manager_name=manager_name,
    )


@router.post("/ai/intake", response_model=BotAIIntakeOut)
def ai_intake(payload: BotAIIntakeIn, db: Session = Depends(get_db)) -> BotAIIntakeOut:
    """ИИ-ветка BPMN: извлечение, дубликаты, практика, команда, цена, SLA и КП."""
    bot_user = get_bot_user(db, payload.telegram_id)
    return BotAIIntakeOut.model_validate(
        analyze_intake(
            db,
            telegram_id=payload.telegram_id,
            text=payload.text,
            client_name=payload.client_name or bot_user.full_name,
            company=payload.company,
        )
    )


@router.post("/orders", response_model=BotOrderOut, status_code=status.HTTP_201_CREATED)
def create_bot_order(payload: BotOrderIn, db: Session = Depends(get_db)) -> BotOrderOut:
    bot_user = get_bot_user(db, payload.telegram_id)

    client = db.scalar(
        select(Client).where(Client.telegram_id == payload.telegram_id)
    )
    if client is None:
        client = Client(
            name=payload.client_name
            or bot_user.full_name
            or f"Клиент {payload.telegram_id}",
            contact_person=bot_user.full_name or None,
            phone=payload.phone or bot_user.phone,
            email=payload.email or bot_user.email,
            telegram_id=payload.telegram_id,
        )
        db.add(client)
        db.flush()
    else:
        if payload.client_name:
            client.name = payload.client_name
        if payload.phone:
            client.phone = payload.phone

    calc = estimate(payload.practice.value, payload.hours, payload.complexity)
    manager = db.scalar(
        select(User).where(
            User.is_active.is_(True), User.role == UserRole.MANAGER.value
        )
    )
    is_vk = payload.telegram_id < 0
    source = "vk" if is_vk else "telegram"

    order = create_order(
        db,
        client=client,
        practice=payload.practice.value,
        title=payload.title,
        description=payload.description,
        manager_id=manager.id if manager else None,
        amount=calc["amount"],
        source=source,
        bot_user=bot_user,
        actor_type=ActorType.BOT.value,
        actor_id=bot_user.id,
        comment=(
            "Заявка создана через VK-бота (ИИ-разбор)"
            if is_vk and payload.kp
            else "Заявка создана через VK-бота"
            if is_vk
            else "Заявка создана через Telegram-бота"
        ),
    )

    if payload.kp:
        create_ai_proposal(db, order, payload.kp)
        db.commit()

    return BotOrderOut(
        id=order.id,
        number=order.number,
        title=order.title,
        status=order.status,
        status_label=STATUS_LABELS.get(order.status, order.status),
        practice=order.practice,
        practice_label=PRACTICE_LABELS.get(order.practice, order.practice),
        amount=float(order.amount),
        created_at=order.created_at,
        sla_due_at=order.sla_due_at,
        estimate=BotEstimateOut(
            rate=calc["rate"],
            hours=calc["hours"],
            multiplier=calc["multiplier"],
            amount=calc["amount"],
            sla_hours=calc["sla_hours"],
        ),
    )


@router.get("/orders", response_model=list[BotOrderShort])
def client_orders(
    telegram_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[BotOrderShort]:
    bot_user = get_bot_user(db, telegram_id)
    query = (
        select(Order)
        .join(Client)
        .where(Client.telegram_id == telegram_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    if bot_user.role == BotRole.MANAGER.value:
        query = select(Order).order_by(Order.created_at.desc()).limit(limit)

    orders = db.scalars(query).all()
    return [
        BotOrderShort(
            id=order.id,
            number=order.number,
            title=order.title,
            status=order.status,
            status_label=STATUS_LABELS.get(order.status, order.status),
            amount=float(order.amount),
            created_at=order.created_at,
        )
        for order in orders
    ]


@router.get("/orders/{number}", response_model=BotOrderDetailOut)
def client_order_detail(
    number: str,
    telegram_id: int,
    db: Session = Depends(get_db),
) -> BotOrderDetailOut:
    bot_user = get_bot_user(db, telegram_id)
    order = db.scalar(
        select(Order)
        .where(Order.number == number)
        .options(selectinload(Order.client), selectinload(Order.events))
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    is_owner = order.client is not None and order.client.telegram_id == telegram_id
    is_manager = bot_user.role == BotRole.MANAGER.value
    if not (is_owner or is_manager):
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

    return BotOrderDetailOut(
        id=order.id,
        number=order.number,
        title=order.title,
        status=order.status,
        status_label=STATUS_LABELS.get(order.status, order.status),
        amount=float(order.amount),
        created_at=order.created_at,
        practice=order.practice,
        practice_label=PRACTICE_LABELS.get(order.practice, order.practice),
        client_name=order.client.name if order.client else None,
        description=order.description,
        sla_due_at=order.sla_due_at,
        is_overdue=order.is_overdue,
        events=[OrderEventOut.model_validate(event) for event in order.events],
    )


@router.get("/queue", response_model=list[BotOrderShort])
def manager_queue(
    telegram_id: int,
    db: Session = Depends(get_db),
) -> list[BotOrderShort]:
    bot_user = get_bot_user(db, telegram_id)
    ensure_manager(bot_user)

    orders = db.scalars(
        select(Order)
        .where(
            Order.status.in_(
                [
                    OrderStatus.NEW.value,
                    OrderStatus.CLARIFICATION.value,
                    OrderStatus.QUALIFIED.value,
                    OrderStatus.REVISION.value,
                ]
            )
        )
        .order_by(Order.created_at.asc())
        .limit(20)
    ).all()
    return [
        BotOrderShort(
            id=order.id,
            number=order.number,
            title=order.title,
            status=order.status,
            status_label=STATUS_LABELS.get(order.status, order.status),
            amount=float(order.amount),
            created_at=order.created_at,
        )
        for order in orders
    ]


@router.post("/orders/{order_id}/status", response_model=BotOrderDetailOut)
def bot_change_status(
    order_id: int,
    payload: BotStatusIn,
    db: Session = Depends(get_db),
) -> BotOrderDetailOut:
    bot_user = get_bot_user(db, payload.telegram_id)
    ensure_manager(bot_user)

    order = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.client), selectinload(Order.events))
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    try:
        change_status(
            db,
            order,
            payload.status.value,
            actor_type=ActorType.BOT.value,
            actor_id=bot_user.id,
            comment=payload.comment or "Статус изменён через Telegram-бота",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.refresh(order)
    return BotOrderDetailOut(
        id=order.id,
        number=order.number,
        title=order.title,
        status=order.status,
        status_label=STATUS_LABELS.get(order.status, order.status),
        amount=float(order.amount),
        created_at=order.created_at,
        practice=order.practice,
        practice_label=PRACTICE_LABELS.get(order.practice, order.practice),
        client_name=order.client.name if order.client else None,
        description=order.description,
        sla_due_at=order.sla_due_at,
        is_overdue=order.is_overdue,
        events=[OrderEventOut.model_validate(event) for event in order.events],
    )


@router.get("/stats", response_model=BotStatsOut)
def bot_stats(telegram_id: int, db: Session = Depends(get_db)) -> BotStatsOut:
    bot_user = get_bot_user(db, telegram_id)
    ensure_manager(bot_user)

    dashboard = build_dashboard(db)
    new_orders = db.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.NEW.value)
    ) or 0
    return BotStatsOut(
        orders_total=dashboard.summary.orders_total,
        active_orders=dashboard.summary.active_orders,
        paid_total=dashboard.summary.paid_total,
        profit=dashboard.summary.profit,
        overdue_count=dashboard.summary.overdue_count,
        conversion=dashboard.summary.conversion,
        new_orders=int(new_orders),
        generated_at=dashboard.generated_at,
    )


@router.post("/link", response_model=BotLinkOut)
def dashboard_link(payload: BotUserIn, db: Session = Depends(get_db)) -> BotLinkOut:
    bot_user = get_bot_user(db, payload.telegram_id)
    if bot_user.role != BotRole.MANAGER.value or bot_user.user_id is None:
        raise HTTPException(
            status_code=403,
            detail="Дашборд доступен только сотрудникам. Обратитесь к администратору.",
        )

    settings = get_settings()
    token = create_magic_token(bot_user.user_id)
    url = f"{settings.frontend_url.rstrip('/')}/magic?token={token}"
    return BotLinkOut(url=url, expires_in_minutes=settings.magic_link_expire_minutes)


@router.get("/notifications", response_model=list[NotificationOut])
def pending_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    items = db.scalars(
        select(Notification)
        .where(Notification.status == "pending")
        .order_by(Notification.created_at.asc())
        .limit(limit)
    ).all()
    return [NotificationOut.model_validate(item) for item in items]


@router.post("/notifications/ack")
def ack_notifications(payload: NotificationAckIn, db: Session = Depends(get_db)) -> dict:
    if not payload.ids:
        return {"updated": 0}
    items = db.scalars(
        select(Notification).where(Notification.id.in_(payload.ids))
    ).all()
    for item in items:
        item.status = "sent"
        item.sent_at = utcnow()
    db.commit()
    return {"updated": len(items)}


@router.get("/pricing")
def bot_pricing() -> dict:
    return pricing_info()
