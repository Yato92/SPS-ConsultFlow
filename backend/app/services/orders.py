"""Бизнес-логика заказов: создание, смена статуса, уведомления, аудит."""

import html
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    ACTIVE_STATUSES,
    PRACTICE_LABELS,
    STATUS_LABELS,
    STATUS_TRANSITIONS,
    ActorType,
    DocumentType,
    OrderStatus,
    UserRole,
)
from app.core.utils import format_money, to_money, utcnow
from app.models import AuditLog, BotUser, Client, Document, Notification, Order, OrderEvent, User
from app.services.documents import build_document, document_for_status
from app.services.pricing import get_sla_hours


def audit(
    db: Session,
    action: str,
    *,
    actor_type: str = ActorType.SYSTEM.value,
    actor_id: int | None = None,
    entity: str | None = None,
    entity_id: str | int | None = None,
    meta: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            meta=meta or {},
        )
    )


def next_order_number(db: Session) -> str:
    year = utcnow().year
    last_id = db.scalar(select(func.max(Order.id))) or 0
    return f"CF-{year}-{last_id + 1:04d}"


def _notify(db: Session, order: Order, recipients: list[str], text: str) -> None:
    for recipient in dict.fromkeys(recipients):
        if not recipient:
            continue
        db.add(
            Notification(
                order_id=order.id,
                channel="telegram",
                recipient=str(recipient),
                text=text,
                status="pending",
            )
        )


def notify_managers(db: Session, order: Order, header: str) -> None:
    managers = db.scalars(
        select(User).where(
            User.is_active.is_(True),
            User.telegram_id.is_not(None),
            User.role.in_([UserRole.ADMIN.value, UserRole.MANAGER.value]),
        )
    ).all()
    recipients = [str(user.telegram_id) for user in managers if user.telegram_id]
    bot_managers = db.scalars(
        select(BotUser).where(
            BotUser.is_active.is_(True),
            BotUser.role == "manager",
        )
    ).all()
    recipients.extend(str(item.telegram_id) for item in bot_managers)
    text = (
        f"<b>{html.escape(header)}</b>\n"
        f"Заказ <b>{order.number}</b> · {html.escape(PRACTICE_LABELS.get(order.practice, order.practice))}\n"
        f"{html.escape(order.title)}\n"
        f"Клиент: {html.escape(order.client.name if order.client else '—')}\n"
        f"Сумма: {format_money(order.amount)}\n"
        f"Статус: {STATUS_LABELS.get(order.status, order.status)}"
    )
    _notify(db, order, recipients, text)


def notify_client(db: Session, order: Order, header: str) -> None:
    recipients: list[str] = []
    if order.client and order.client.telegram_id:
        recipients.append(str(order.client.telegram_id))
    if order.bot_user and order.bot_user.telegram_id:
        recipients.append(str(order.bot_user.telegram_id))
    text = (
        f"<b>{html.escape(header)}</b>\n"
        f"Заказ <b>{order.number}</b>: {html.escape(order.title)}\n"
        f"Новый статус: {STATUS_LABELS.get(order.status, order.status)}"
    )
    _notify(db, order, recipients, text)


def create_order(
    db: Session,
    *,
    client: Client,
    practice: str,
    title: str,
    description: str | None = None,
    manager_id: int | None = None,
    amount: float | Decimal = 0,
    deadline: date | None = None,
    source: str = "dashboard",
    bot_user: BotUser | None = None,
    actor_type: str = ActorType.USER.value,
    actor_id: int | None = None,
    comment: str | None = None,
) -> Order:
    now = utcnow()
    order = Order(
        number=next_order_number(db),
        client=client,
        practice=practice,
        title=title.strip(),
        description=description,
        manager_id=manager_id,
        amount=to_money(amount),
        status=OrderStatus.NEW.value,
        deadline=deadline,
        sla_due_at=now.replace(microsecond=0) + timedelta(hours=get_sla_hours(practice)),
        source=source,
        bot_user_id=bot_user.id if bot_user else None,
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.flush()

    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.NEW.value,
            comment=comment or "Заявка создана",
            actor_type=actor_type,
            actor_id=actor_id,
        )
    )
    audit(
        db,
        "order.created",
        actor_type=actor_type,
        actor_id=actor_id,
        entity="order",
        entity_id=order.id,
        meta={"number": order.number, "source": source},
    )
    notify_managers(db, order, "Новая заявка ConsultFlow")
    db.commit()
    db.refresh(order)
    return order


def create_document_record(
    db: Session,
    order: Order,
    doc_type: str,
    *,
    actor_type: str = ActorType.SYSTEM.value,
    actor_id: int | None = None,
    commit: bool = True,
) -> Document:
    payload = build_document(order, doc_type)
    document = Document(
        order_id=order.id,
        doc_type=doc_type,
        number=payload["number"],
        status="draft",
        payload=payload,
    )
    db.add(document)
    audit(
        db,
        "document.generated",
        actor_type=actor_type,
        actor_id=actor_id,
        entity="document",
        entity_id=order.id,
        meta={"doc_type": doc_type, "number": payload["number"]},
    )
    if commit:
        db.commit()
        db.refresh(document)
    return document


def change_status(
    db: Session,
    order: Order,
    new_status: str,
    *,
    actor_type: str = ActorType.USER.value,
    actor_id: int | None = None,
    comment: str | None = None,
    force: bool = False,
    create_documents: bool = True,
) -> Order:
    new_status = str(new_status)
    if order.status == new_status:
        raise ValueError("Заказ уже находится в этом статусе")

    allowed = STATUS_TRANSITIONS.get(order.status, set())
    if not force and new_status not in allowed:
        raise ValueError(
            f"Переход «{STATUS_LABELS.get(order.status, order.status)}» → "
            f"«{STATUS_LABELS.get(new_status, new_status)}» недопустим"
        )

    old_status = order.status
    order.status = new_status
    order.updated_at = utcnow()
    if new_status == OrderStatus.CLOSED.value:
        order.closed_at = utcnow()

    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=old_status,
            to_status=new_status,
            comment=comment,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    )
    audit(
        db,
        "order.status_changed",
        actor_type=actor_type,
        actor_id=actor_id,
        entity="order",
        entity_id=order.id,
        meta={"from": old_status, "to": new_status},
    )

    doc_type = document_for_status(order, new_status)
    if doc_type and create_documents:
        create_document_record(
            db, order, doc_type, actor_type=actor_type, actor_id=actor_id, commit=False
        )

    notify_client(db, order, "Статус заказа обновлён")
    db.commit()
    db.refresh(order)
    return order


def update_order_fields(
    db: Session,
    order: Order,
    data: dict,
    *,
    actor_id: int | None = None,
) -> Order:
    allowed = {
        "title",
        "description",
        "practice",
        "manager_id",
        "amount",
        "paid_amount",
        "expenses",
        "deadline",
    }
    changed: dict[str, str] = {}
    for field, value in data.items():
        if field not in allowed or value is None:
            continue
        if field in {"amount", "paid_amount", "expenses"}:
            value = to_money(value)
        if getattr(order, field) != value:
            changed[field] = str(value)
            setattr(order, field, value)
    if changed:
        order.updated_at = utcnow()
        audit(
            db,
            "order.updated",
            actor_type=ActorType.USER.value,
            actor_id=actor_id,
            entity="order",
            entity_id=order.id,
            meta=changed,
        )
        db.commit()
        db.refresh(order)
    return order


def active_orders_query():
    return select(Order).where(Order.status.in_(ACTIVE_STATUSES))
