"""Действия клиента и сотрудника по заявке прямо в VK-боте.

Сервис переиспользует бизнес-логику ConsultFlow: статусы, документы, workflow
и уведомления. Клиент видит только свои заявки; сотрудник — очередь и смену
статуса. Все действия пишутся в ту же базу, что и React-дашборд.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    DOCUMENT_LABELS,
    PRACTICE_LABELS,
    STATUS_LABELS,
    STATUS_TRANSITIONS,
    ActorType,
    DocumentType,
    OrderStatus,
)
from app.core.utils import format_money, to_money, utcnow
from app.models import Document, Order, OrderEvent
from app.services.orders import (
    change_status,
    create_document_record,
    notify_managers,
)
from app.services.prototype import ensure_workflow

# Подписи кнопок сотрудника: короткие, чтобы помещались в VK.
MANAGER_ACTION_LABELS: dict[str, str] = {
    OrderStatus.CLARIFICATION.value: "❓ Уточнить",
    OrderStatus.QUALIFIED.value: "✅ Квалифицировать",
    OrderStatus.PROPOSAL.value: "📄 Отправить КП",
    OrderStatus.REVISION.value: "✍️ На доработку",
    OrderStatus.APPROVED.value: "✅ Согласовать КП",
    OrderStatus.CONTRACT.value: "📑 Договор",
    OrderStatus.IN_PROGRESS.value: "▶️ В работу",
    OrderStatus.DONE.value: "🏁 Работа выполнена",
    OrderStatus.CLOSED.value: "✅ Закрыть заявку",
    OrderStatus.CANCELLED.value: "❌ Отменить заявку",
}

CLIENT_ACTION_LABELS: dict[str, str] = {
    "read": "📄 Прочитать документы",
    "answer": "💬 Ответить на уточнение",
    "sign": "✅ Подписать КП",
    "remarks": "✍️ Замечания к КП",
    "pay": "💳 Тестовая оплата",
    "confirm": "✅ Подтвердить работу",
    "refresh": "🔄 Обновить статус",
}

PAYABLE_STATUSES = {
    OrderStatus.APPROVED.value,
    OrderStatus.CONTRACT.value,
    OrderStatus.IN_PROGRESS.value,
    OrderStatus.DONE.value,
}


class BotClientError(ValueError):
    """Действие недоступно или данные некорректны."""


def load_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.is_deleted.is_(False))
        .options(
            selectinload(Order.client),
            selectinload(Order.manager),
            selectinload(Order.documents),
            selectinload(Order.events),
            selectinload(Order.workflow),
        )
        .execution_options(populate_existing=True)
    )


def _is_paid(order: Order) -> bool:
    amount = to_money(order.amount or 0)
    return amount > 0 and to_money(order.paid_amount or 0) >= amount


def _has_document(order: Order, doc_type: str) -> bool:
    return any(doc.doc_type == doc_type for doc in order.documents)


def _document_payload(order: Order) -> list[dict]:
    items = sorted(
        order.documents, key=lambda doc: (doc.created_at or utcnow(), doc.id)
    )
    result: list[dict] = []
    for doc in items:
        payload = doc.payload or {}
        body = payload.get("body") or payload.get("text")
        result.append(
            {
                "id": doc.id,
                "type": doc.doc_type,
                "label": DOCUMENT_LABELS.get(doc.doc_type, doc.doc_type),
                "number": doc.number,
                "status": doc.status,
                "body": body,
                "created_at": doc.created_at,
            }
        )
    return result


def _is_act_confirmed(order: Order) -> bool:
    workflow = order.workflow
    if workflow is not None and workflow.act_confirmed_at is not None:
        return True
    act = _latest_document(order, DocumentType.ACT.value)
    return bool(act is not None and act.status == "signed")


def available_client_actions(order: Order) -> list[dict]:
    """Кнопки клиента, доступные в текущем статусе заявки."""
    if order.status in {OrderStatus.CANCELLED.value}:
        return [{"code": "read", "label": CLIENT_ACTION_LABELS["read"], "value": None}]

    actions: list[dict] = [
        {"code": "read", "label": CLIENT_ACTION_LABELS["read"], "value": None}
    ]

    if order.status == OrderStatus.CLARIFICATION.value:
        actions.append(
            {"code": "answer", "label": CLIENT_ACTION_LABELS["answer"], "value": None}
        )

    if order.status == OrderStatus.PROPOSAL.value:
        actions.append(
            {"code": "sign", "label": CLIENT_ACTION_LABELS["sign"], "value": None}
        )
        actions.append(
            {"code": "remarks", "label": CLIENT_ACTION_LABELS["remarks"], "value": None}
        )

    if order.status in PAYABLE_STATUSES and not _is_paid(order):
        actions.append(
            {"code": "pay", "label": CLIENT_ACTION_LABELS["pay"], "value": None}
        )

    if (
        order.status in {OrderStatus.IN_PROGRESS.value, OrderStatus.DONE.value}
        and _has_document(order, DocumentType.ACT.value)
        and not _is_act_confirmed(order)
    ):
        actions.append(
            {"code": "confirm", "label": CLIENT_ACTION_LABELS["confirm"], "value": None}
        )

    return actions


def available_manager_actions(order: Order) -> list[dict]:
    """Кнопки сотрудника: допустимые переходы статуса."""
    allowed = STATUS_TRANSITIONS.get(order.status, set())
    actions: list[dict] = []
    for target in (
        OrderStatus.QUALIFIED.value,
        OrderStatus.PROPOSAL.value,
        OrderStatus.APPROVED.value,
        OrderStatus.CONTRACT.value,
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.DONE.value,
        OrderStatus.CLOSED.value,
        OrderStatus.CLARIFICATION.value,
        OrderStatus.REVISION.value,
        OrderStatus.CANCELLED.value,
    ):
        if target in allowed:
            actions.append(
                {
                    "code": "status",
                    "label": MANAGER_ACTION_LABELS.get(
                        target, STATUS_LABELS.get(target, target)
                    ),
                    "value": target,
                }
            )
    return actions[:4]


def client_order_payload(
    order: Order, *, manager_actions: bool = False
) -> dict:
    return {
        "id": order.id,
        "number": order.number,
        "title": order.title,
        "description": order.description,
        "status": order.status,
        "status_label": STATUS_LABELS.get(order.status, order.status),
        "practice": order.practice,
        "practice_label": PRACTICE_LABELS.get(order.practice, order.practice),
        "amount": float(order.amount or 0),
        "paid_amount": float(order.paid_amount or 0),
        "created_at": order.created_at,
        "documents": _document_payload(order),
        "actions": available_client_actions(order),
        "manager_actions": available_manager_actions(order) if manager_actions else [],
    }


def _add_event(order: Order, comment: str) -> None:
    order.events.append(
        OrderEvent(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            comment=comment,
            actor_type=ActorType.USER.value,
        )
    )


def _latest_document(order: Order, doc_type: str) -> Document | None:
    items = [doc for doc in order.documents if doc.doc_type == doc_type]
    if not items:
        return None
    items.sort(key=lambda doc: (doc.created_at or utcnow(), doc.id))
    return items[-1]


def apply_client_action(
    db: Session, order: Order, action: str, value: str | None = None
) -> None:
    available = {item["code"] for item in available_client_actions(order)}
    if action not in available:
        raise BotClientError(
            f"Действие «{CLIENT_ACTION_LABELS.get(action, action)}» сейчас недоступно. "
            f"Текущий статус: {STATUS_LABELS.get(order.status, order.status)}."
        )

    if action == "read":
        return

    if action == "answer":
        text = (value or "").strip()
        if len(text) < 2:
            raise BotClientError("Напишите ответ одним сообщением.")
        workflow = ensure_workflow(db, order)
        workflow.clarification_answer = text
        _add_event(order, "Ответ клиента получен через VK")
        notify_managers(db, order, "Ответ клиента по заявке (VK)")
        db.commit()
        return

    if action == "sign":
        proposal = _latest_document(order, DocumentType.PROPOSAL.value)
        if proposal is None:
            proposal = create_document_record(
                db,
                order,
                DocumentType.PROPOSAL.value,
                actor_type=ActorType.USER.value,
                commit=False,
            )
        proposal.status = "signed"
        workflow = ensure_workflow(db, order)
        workflow.signed_at = workflow.signed_at or utcnow()
        if order.status == OrderStatus.PROPOSAL.value:
            change_status(
                db,
                order,
                OrderStatus.APPROVED.value,
                actor_type=ActorType.USER.value,
                comment="КП подписано клиентом в VK",
                notify=False,
            )
        else:
            _add_event(order, "КП подписано клиентом в VK")
            db.commit()
        notify_managers(db, order, "Клиент подписал КП в VK")
        db.commit()
        return

    if action == "remarks":
        text = (value or "").strip()
        if len(text) < 2:
            raise BotClientError("Опишите замечания одним сообщением.")
        workflow = ensure_workflow(db, order)
        workflow.remarks = text
        change_status(
            db,
            order,
            OrderStatus.REVISION.value,
            actor_type=ActorType.USER.value,
            comment="Замечания клиента из VK",
            notify=False,
        )
        notify_managers(db, order, "Замечания клиента по КП (VK)")
        db.commit()
        return

    if action == "pay":
        amount = to_money(order.amount or 0)
        if amount <= 0:
            raise BotClientError("В заявке не указана стоимость.")
        if _is_paid(order):
            raise BotClientError("Заявка уже оплачена.")
        paid_at = utcnow()
        order.paid_amount = amount
        order.updated_at = paid_at
        document = create_document_record(
            db,
            order,
            DocumentType.PAYMENT.value,
            actor_type=ActorType.USER.value,
            commit=False,
        )
        document.status = "paid"
        document.payload = {
            **(document.payload or {}),
            "paid_at": paid_at.isoformat(),
            "amount": format_money(amount),
            "test": True,
            "channel": "vk",
        }
        _add_event(order, f"Тестовая оплата {format_money(amount)} через VK")
        notify_managers(db, order, "Клиент оплатил заявку в VK (тестовый платёж)")
        db.commit()
        return

    if action == "confirm":
        act = _latest_document(order, DocumentType.ACT.value)
        if act is None:
            raise BotClientError(
                "Акт ещё не сформирован. Дождитесь, когда сотрудник завершит работу."
            )
        if _is_act_confirmed(order):
            raise BotClientError("Работа по этой заявке уже подтверждена.")
        if order.status == OrderStatus.IN_PROGRESS.value:
            # Клиент принимает работу: заявка переходит в «Работа выполнена»,
            # а сотрудник получает уведомление и закрывает её.
            change_status(
                db,
                order,
                OrderStatus.DONE.value,
                actor_type=ActorType.USER.value,
                comment="Акт подтверждён клиентом в VK",
                create_documents=False,
                notify=False,
            )
            order = load_order(db, order.id) or order
            act = _latest_document(order, DocumentType.ACT.value) or act
        elif order.status == OrderStatus.DONE.value:
            change_status(
                db,
                order,
                OrderStatus.CLOSED.value,
                actor_type=ActorType.USER.value,
                comment="Работа подтверждена клиентом в VK",
                create_documents=False,
                notify=False,
            )
            order = load_order(db, order.id) or order
            act = _latest_document(order, DocumentType.ACT.value) or act
        elif order.status != OrderStatus.CLOSED.value:
            raise BotClientError(
                "Подтвердить работу можно после того, как сотрудник завершит её."
            )
        act.status = "signed"
        workflow = ensure_workflow(db, order)
        workflow.act_confirmed_at = workflow.act_confirmed_at or utcnow()
        notify_managers(db, order, "Клиент подтвердил работу в VK")
        db.commit()
        return

    raise BotClientError("Неизвестное действие.")


def apply_manager_action(
    db: Session, order: Order, action: str, value: str | None = None
) -> None:
    if action != "status" or not value:
        raise BotClientError("Неизвестное действие сотрудника.")
    target = str(value)
    allowed = STATUS_TRANSITIONS.get(order.status, set())
    if target not in allowed:
        raise BotClientError(
            f"Переход «{STATUS_LABELS.get(order.status, order.status)}» → "
            f"«{STATUS_LABELS.get(target, target)}» недопустим."
        )
    change_status(
        db,
        order,
        target,
        actor_type=ActorType.BOT.value,
        comment="Статус изменён сотрудником в VK-боте",
    )
