"""Публичный личный кабинет клиента по одноразовой ссылке из бота."""

from __future__ import annotations

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.enums import PRACTICE_LABELS, STATUS_LABELS
from app.core.security import TOKEN_CLIENT, create_client_token, decode_token
from app.core.utils import utcnow
from app.models import Client, Document, Order, OrderStatus
from app.schemas import (
    ClientPortalDocumentOut,
    ClientPortalOrderOut,
    ClientPortalOut,
)

DOCUMENT_LABELS = {
    "proposal": "Коммерческое предложение",
    "contract": "Договор",
    "act": "Акт выполненных работ",
    "payment": "Чек об оплате",
}


class InvalidClientLink(ValueError):
    """Ссылка в кабинет недействительна или устарела."""


def build_client_url(client_id: int) -> tuple[str, int]:
    """Вернуть ссылку на кабинет и срок её действия в минутах."""
    settings = get_settings()
    token = create_client_token(client_id)
    base = settings.frontend_url.rstrip("/")
    return f"{base}/client?token={token}", settings.client_link_expire_minutes


def _document_out(document: Document) -> ClientPortalDocumentOut:
    return ClientPortalDocumentOut(
        id=document.id,
        type=document.doc_type,
        name=DOCUMENT_LABELS.get(document.doc_type, document.doc_type),
        status=document.status,
        created_at=document.created_at or utcnow(),
    )


def _order_out(order: Order) -> ClientPortalOrderOut:
    documents = [
        _document_out(document)
        for document in order.documents
        if document.doc_type in DOCUMENT_LABELS
    ]
    documents.sort(key=lambda item: item.created_at)
    return ClientPortalOrderOut(
        id=order.id,
        number=order.number,
        title=order.title,
        description=order.description,
        status=order.status,
        status_label=STATUS_LABELS.get(order.status, order.status),
        practice=order.practice,
        practice_label=PRACTICE_LABELS.get(order.practice, order.practice),
        amount=float(order.amount),
        paid_amount=float(order.paid_amount),
        created_at=order.created_at,
        sla_due_at=order.sla_due_at,
        is_overdue=order.is_overdue,
        documents=documents,
    )


def client_portal(db: Session, token: str) -> ClientPortalOut:
    try:
        claims = decode_token(token)
    except jwt.PyJWTError as exc:
        raise InvalidClientLink("Ссылка недействительна или устарела") from exc

    if claims.get("type") != TOKEN_CLIENT:
        raise InvalidClientLink("Неверный тип ссылки")

    try:
        client_id = int(claims.get("sub", 0))
    except (TypeError, ValueError) as exc:
        raise InvalidClientLink("Некорректная ссылка") from exc

    client = db.get(Client, client_id)
    if client is None:
        raise InvalidClientLink("Клиент не найден")

    orders = list(
        db.scalars(
            select(Order)
            .where(
                Order.client_id == client.id,
                Order.status != OrderStatus.CANCELLED.value,
            )
            .options(selectinload(Order.documents))
            .order_by(Order.created_at.desc(), Order.id.desc())
        ).all()
    )
    return ClientPortalOut(
        client_name=client.name,
        contact_person=client.contact_person,
        orders=[_order_out(order) for order in orders],
    )
