"""Сервис учебного прототипа ConsultFlow.

Прототип работает с теми же таблицами заказов, клиентов и документов, что и
основное приложение, поэтому изменения сразу видны в Telegram-боте и дашборде.
Дополнительные поля сценария (уточнения, замечания, версии КП) хранятся в
отдельной таблице ``order_workflows``.
"""

import re
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    PRACTICE_LABELS,
    STATUS_LABELS,
    ActorType,
    DocumentType,
    OrderStatus,
    Practice,
)
from app.core.utils import format_money, to_money, utcnow
from app.models import Client, Order, OrderEvent, OrderWorkflow, User
from app.schemas import (
    PrototypeAnswerIn,
    PrototypeBootstrapOut,
    PrototypeClarifyIn,
    PrototypeDocumentOut,
    PrototypeHistoryOut,
    PrototypeOrderCreate,
    PrototypeOrderOut,
    PrototypePaymentIn,
    PrototypePracticeIn,
    PrototypeProposalIn,
    PrototypeRemarksIn,
)
from app.services.orders import (
    change_status,
    create_document_record,
    create_order,
    notify_client,
    notify_managers,
    update_order_fields,
)

DEMO_CLIENT_NAME = "ООО «Вектор»"
DEMO_BOT_TELEGRAM_ID = 700000001

PROTOTYPE_CONSULTANTS = [
    "Анна Смирнова",
    "Дмитрий Орлов",
    "Мария Ковалёва",
]

DEFAULT_SLA = "Ответ на обращение в течение 1 рабочего дня"
DEFAULT_FILE = "Техническое задание.pdf"


class PrototypeError(ValueError):
    """Ошибка сценария прототипа, которую можно показать пользователю."""


def _load_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.client),
            selectinload(Order.manager),
            selectinload(Order.events),
            selectinload(Order.documents),
            selectinload(Order.workflow),
        )
    )


def ensure_workflow(db: Session, order: Order) -> OrderWorkflow:
    if order.workflow is not None:
        return order.workflow

    workflow = OrderWorkflow(
        order_id=order.id,
        display_number=None,
        file_name=DEFAULT_FILE,
        consultant_name=PROTOTYPE_CONSULTANTS[0],
        solution=None,
        duration_days=5,
        sla_text=DEFAULT_SLA,
        practice_confirmed=False,
    )
    db.add(workflow)
    db.flush()
    order.workflow = workflow
    return workflow


def next_display_number(db: Session) -> str:
    values: list[int] = []
    for value in db.scalars(select(OrderWorkflow.display_number)).all():
        if value and str(value).isdigit():
            values.append(int(value))
    return str(max(values + [104]) + 1)


def prototype_status(order: Order, workflow: OrderWorkflow) -> str:
    if order.status in {OrderStatus.DONE.value, OrderStatus.CLOSED.value}:
        return "done"
    if order.status == OrderStatus.IN_PROGRESS.value:
        return "in_progress"
    if order.status == OrderStatus.REVISION.value:
        return "revision"
    if order.status in {
        OrderStatus.PROPOSAL.value,
        OrderStatus.APPROVED.value,
        OrderStatus.CONTRACT.value,
    }:
        return "sent"
    if order.status == OrderStatus.CLARIFICATION.value:
        return "clarification"
    if (
        workflow.clarification_question
        and not workflow.clarification_answer
        and order.status in {OrderStatus.NEW.value, OrderStatus.QUALIFIED.value}
    ):
        return "clarification"
    return "new"


def _document_list(order: Order, workflow: OrderWorkflow) -> list[PrototypeDocumentOut]:
    proposals = [
        doc for doc in order.documents if doc.doc_type == DocumentType.PROPOSAL.value
    ]
    proposals.sort(key=lambda doc: doc.created_at or utcnow())
    result: list[PrototypeDocumentOut] = []
    for index, doc in enumerate(proposals, start=1):
        signed = doc.status == "signed" or (
            workflow.signed_at is not None and index == len(proposals)
        )
        result.append(
            PrototypeDocumentOut(
                id=doc.id,
                type="proposal",
                name="Подписанное КП.pdf" if signed else f"КП — версия {index}.pdf",
                status=doc.status,
                created_at=doc.created_at or utcnow(),
            )
        )
    for doc in order.documents:
        if doc.doc_type == DocumentType.CONTRACT.value:
            result.append(
                PrototypeDocumentOut(
                    id=doc.id,
                    type="contract",
                    name="Договор.pdf",
                    status=doc.status,
                    created_at=doc.created_at or utcnow(),
                )
            )
        elif doc.doc_type == DocumentType.ACT.value:
            result.append(
                PrototypeDocumentOut(
                    id=doc.id,
                    type="act",
                    name="Акт выполненных работ.pdf",
                    status=doc.status,
                    created_at=doc.created_at or utcnow(),
                )
            )
        elif doc.doc_type == DocumentType.PAYMENT.value:
            result.append(
                PrototypeDocumentOut(
                    id=doc.id,
                    type="payment",
                    name="Чек об оплате.pdf",
                    status=doc.status,
                    created_at=doc.created_at or utcnow(),
                )
            )
    return result


def _history(order: Order) -> list[PrototypeHistoryOut]:
    events = sorted(order.events, key=lambda event: event.created_at or utcnow())
    items: list[PrototypeHistoryOut] = []
    for event in events:
        text = event.comment or STATUS_LABELS.get(event.to_status, event.to_status)
        created = event.created_at or utcnow()
        items.append(
            PrototypeHistoryOut(
                text=text,
                time=created.strftime("%H:%M")
                if created.date() == utcnow().date()
                else created.strftime("%d.%m %H:%M"),
            )
        )
    if not items:
        items.append(PrototypeHistoryOut(text="Заявка зарегистрирована", time="—"))
    return items


def serialize_order(
    db: Session, order: Order, *, ensure: bool = True
) -> PrototypeOrderOut:
    workflow = ensure_workflow(db, order) if ensure else order.workflow
    if workflow is None:
        workflow = OrderWorkflow(order_id=order.id)
    proposals = [
        doc for doc in order.documents if doc.doc_type == DocumentType.PROPOSAL.value
    ]
    proposal_version = max(workflow.proposal_version, len(proposals))
    signed = (
        workflow.signed_at is not None
        or any(doc.status == "signed" for doc in proposals)
        or (
            bool(proposals)
            and order.status
            in {
                OrderStatus.APPROVED.value,
                OrderStatus.CONTRACT.value,
                OrderStatus.IN_PROGRESS.value,
                OrderStatus.DONE.value,
                OrderStatus.CLOSED.value,
            }
        )
    )
    contract = workflow.contract_at is not None or any(
        doc.doc_type == DocumentType.CONTRACT.value for doc in order.documents
    )
    act = workflow.act_at is not None or any(
        doc.doc_type == DocumentType.ACT.value for doc in order.documents
    )
    act_confirmed = workflow.act_confirmed_at is not None or (
        order.status == OrderStatus.DONE.value
        and any(
            doc.doc_type == DocumentType.ACT.value and doc.status == "signed"
            for doc in order.documents
        )
    )
    payments = [
        doc
        for doc in order.documents
        if doc.doc_type == DocumentType.PAYMENT.value and doc.status == "paid"
    ]
    payments.sort(key=lambda doc: doc.created_at or utcnow())
    last_payment = payments[-1] if payments else None
    amount = float(order.amount or 0)
    paid = last_payment is not None or (
        amount > 0 and float(order.paid_amount or 0) >= amount
    )
    paid_at = last_payment.payload.get("paid_at") if last_payment else None
    payment_last4 = last_payment.payload.get("last4") if last_payment else None

    due = "—"
    if order.deadline:
        due = order.deadline.strftime("%d.%m.%Y")
    elif order.sla_due_at:
        due = order.sla_due_at.strftime("%d.%m.%Y")

    client = order.client
    return PrototypeOrderOut(
        id=order.id,
        number=workflow.display_number or order.number,
        company=client.name if client else "Клиент",
        contact=(client.contact_person if client else None) or "—",
        email=client.email if client else None,
        service=order.title,
        description=order.description,
        file=workflow.file_name or DEFAULT_FILE,
        manager=order.manager.full_name if order.manager else "Алексей Иванов",
        status=prototype_status(order, workflow),
        practice=order.practice,
        practice_label=PRACTICE_LABELS.get(order.practice, order.practice),
        consultant=workflow.consultant_name or PROTOTYPE_CONSULTANTS[0],
        cost=float(order.amount or 0),
        days=workflow.duration_days or 5,
        sla=workflow.sla_text or DEFAULT_SLA,
        solution=workflow.solution or "",
        due=due,
        clarification=workflow.clarification_question,
        answer=workflow.clarification_answer,
        remarks=workflow.remarks,
        proposal_version=proposal_version,
        signed=signed,
        contract=contract,
        work_started=order.status
        in {
            OrderStatus.IN_PROGRESS.value,
            OrderStatus.DONE.value,
            OrderStatus.CLOSED.value,
        }
        or workflow.work_started_at is not None,
        act=act,
        act_confirmed=act_confirmed,
        paid=paid,
        paid_at=paid_at,
        payment_last4=payment_last4,
        practice_confirmed=workflow.practice_confirmed,
        history=_history(order),
        documents=_document_list(order, workflow),
    )


def _demo_client(db: Session) -> Client | None:
    return db.scalar(select(Client).where(Client.name == DEMO_CLIENT_NAME))


def is_demo_order(db: Session, order: Order) -> bool:
    if order.source == "prototype":
        return True
    client = _demo_client(db)
    return bool(client and order.client_id == client.id)


def demo_orders(db: Session, include_external: bool = False) -> list[Order]:
    client = _demo_client(db)
    conditions = [Order.source == "prototype"]
    if include_external:
        # Заявки из VK/Telegram должны быть видны сотруднику в прототипе,
        # а не только в React-дашборде.
        conditions.append(Order.source.in_(("vk", "telegram")))
    if client is not None:
        conditions.append(Order.client_id == client.id)
    return list(
        db.scalars(
            select(Order)
            .where(
                Order.status != OrderStatus.CANCELLED.value,
                or_(*conditions),
            )
            .options(
                selectinload(Order.client),
                selectinload(Order.manager),
                selectinload(Order.events),
                selectinload(Order.documents),
                selectinload(Order.workflow),
            )
            .order_by(Order.created_at.desc(), Order.id.desc())
        ).all()
    )


def bootstrap(
    db: Session,
    order_id: int | None = None,
    include_external: bool = False,
) -> PrototypeBootstrapOut:
    orders = demo_orders(db, include_external=include_external)
    serialized = [serialize_order(db, order) for order in orders]
    current = None
    if serialized:
        current = next(
            (item for item in serialized if item.id == order_id), serialized[0]
        )
    return PrototypeBootstrapOut(
        orders=serialized,
        current=current,
        practices=[
            {"value": practice, "label": label}
            for practice, label in PRACTICE_LABELS.items()
        ],
        consultants=PROTOTYPE_CONSULTANTS,
    )


def get_order(db: Session, order_id: int) -> Order:
    order = _load_order(db, order_id)
    if order is None:
        raise PrototypeError("Заявка не найдена")
    if not is_demo_order(db, order) and order.source not in {"vk", "telegram"}:
        raise PrototypeError("Заявка не найдена")
    return order


def _add_event(
    db: Session, order: Order, text: str, *, to_status: str | None = None
) -> None:
    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=order.status,
            to_status=to_status or order.status,
            comment=text,
            actor_type=ActorType.SYSTEM.value,
        )
    )


def _locked(order: Order) -> bool:
    return order.status in {
        OrderStatus.DONE.value,
        OrderStatus.CLOSED.value,
        OrderStatus.CANCELLED.value,
    }


def create_prototype_order(
    db: Session, payload: PrototypeOrderCreate
) -> PrototypeOrderOut:
    client = db.scalar(
        select(Client).where(Client.email == str(payload.email))
    )
    if client is None:
        client = Client(
            name=payload.company.strip(),
            contact_person=payload.contact.strip(),
            email=str(payload.email),
        )
        db.add(client)
        db.flush()
    else:
        client.name = payload.company.strip()
        client.contact_person = payload.contact.strip()

    manager = db.scalar(select(User).where(User.email == "a.ivanov@consultflow.ru"))
    if manager is None:
        manager = db.scalar(
            select(User).where(User.role.in_(["admin", "manager"])).limit(1)
        )

    order = create_order(
        db,
        client=client,
        practice=Practice.MANAGEMENT.value,
        title=payload.description.strip()[:120],
        description=payload.description.strip(),
        manager_id=manager.id if manager else None,
        amount=0,
        deadline=date.today() + timedelta(days=1),
        source="prototype",
        actor_type=ActorType.SYSTEM.value,
        comment="Заявка зарегистрирована",
    )
    workflow = ensure_workflow(db, order)
    workflow.display_number = next_display_number(db)
    workflow.file_name = payload.file_name or DEFAULT_FILE
    workflow.solution = None
    _add_event(db, order, "Данные извлечены, дубликаты не найдены")
    db.commit()
    db.refresh(order)
    return serialize_order(db, _load_order(db, order.id) or order)


def update_practice(
    db: Session, order: Order, payload: PrototypePracticeIn
) -> PrototypeOrderOut:
    if _locked(order):
        raise PrototypeError("Заявка уже завершена")
    workflow = ensure_workflow(db, order)
    update_order_fields(
        db, order, {"practice": payload.practice.value}, actor_id=None
    )
    workflow.consultant_name = payload.consultant
    if not workflow.practice_confirmed:
        workflow.practice_confirmed = True
        _add_event(db, order, "Практика и консультант подтверждены")
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def request_clarification(
    db: Session, order: Order, payload: PrototypeClarifyIn
) -> PrototypeOrderOut:
    if _locked(order) or order.status in {
        OrderStatus.PROPOSAL.value,
        OrderStatus.REVISION.value,
        OrderStatus.APPROVED.value,
        OrderStatus.CONTRACT.value,
        OrderStatus.IN_PROGRESS.value,
    }:
        raise PrototypeError("Уточнение доступно только до отправки КП")

    workflow = ensure_workflow(db, order)
    workflow.clarification_question = payload.question.strip()
    workflow.clarification_answer = None
    workflow.remarks = None

    if order.status != OrderStatus.CLARIFICATION.value:
        change_status(
            db,
            order,
            OrderStatus.CLARIFICATION.value,
            actor_type=ActorType.SYSTEM.value,
            comment="Уточнение отправлено клиенту",
        )
        order = _load_order(db, order.id) or order
        order.workflow = workflow
    else:
        _add_event(db, order, "Уточнение отправлено клиенту")
        db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def submit_answer(
    db: Session, order: Order, payload: PrototypeAnswerIn
) -> PrototypeOrderOut:
    workflow = ensure_workflow(db, order)
    if not workflow.clarification_question:
        raise PrototypeError("По заявке не запрашивалось уточнение")
    workflow.clarification_answer = payload.answer.strip()
    _add_event(db, order, "Ответ клиента получен")
    notify_managers(db, order, "Ответ клиента по заявке")
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def send_proposal(
    db: Session, order: Order, payload: PrototypeProposalIn
) -> PrototypeOrderOut:
    if _locked(order) or order.status in {
        OrderStatus.APPROVED.value,
        OrderStatus.CONTRACT.value,
        OrderStatus.IN_PROGRESS.value,
    }:
        raise PrototypeError("КП уже согласовано или заказ находится в работе")
    if order.status == OrderStatus.PROPOSAL.value:
        raise PrototypeError("КП уже отправлено клиенту")

    workflow = ensure_workflow(db, order)
    workflow.solution = payload.solution.strip()
    workflow.duration_days = payload.days
    workflow.sla_text = payload.sla.strip()
    workflow.consultant_name = payload.consultant
    workflow.remarks = None
    workflow.proposal_version = max(
        workflow.proposal_version,
        len(
            [
                doc
                for doc in order.documents
                if doc.doc_type == DocumentType.PROPOSAL.value
            ]
        ),
    )
    workflow.proposal_version += 1
    order.amount = to_money(payload.cost)
    order.deadline = date.today() + timedelta(days=payload.days)
    order.updated_at = utcnow()

    target_comment = (
        "Обновлённое КП отправлено"
        if order.status == OrderStatus.REVISION.value
        else "КП отправлено"
    )
    if order.status == OrderStatus.NEW.value:
        change_status(
            db,
            order,
            OrderStatus.QUALIFIED.value,
            actor_type=ActorType.SYSTEM.value,
            comment="Заявка квалифицирована",
            notify=False,
        )
        order = _load_order(db, order.id) or order
        order.workflow = workflow
    change_status(
        db,
        order,
        OrderStatus.PROPOSAL.value,
        actor_type=ActorType.SYSTEM.value,
        comment=target_comment,
    )
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def sign_proposal(db: Session, order: Order) -> PrototypeOrderOut:
    if order.status not in {
        OrderStatus.PROPOSAL.value,
        OrderStatus.APPROVED.value,
    }:
        raise PrototypeError("Подписать можно только отправленное КП")
    proposals = [
        doc for doc in order.documents if doc.doc_type == DocumentType.PROPOSAL.value
    ]
    if not proposals:
        raise PrototypeError("КП ещё не сформировано")
    proposals.sort(key=lambda doc: doc.created_at or utcnow())
    latest = proposals[-1]
    latest.status = "signed"
    workflow = ensure_workflow(db, order)
    workflow.signed_at = workflow.signed_at or utcnow()

    if order.status == OrderStatus.PROPOSAL.value:
        change_status(
            db,
            order,
            OrderStatus.APPROVED.value,
            actor_type=ActorType.SYSTEM.value,
            comment="КП подписано и сохранено",
            notify=False,
        )
    else:
        _add_event(db, order, "КП подписано и сохранено")
        db.commit()
    notify_managers(db, order, "Клиент подписал КП")
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def submit_remarks(
    db: Session, order: Order, payload: PrototypeRemarksIn
) -> PrototypeOrderOut:
    if order.status != OrderStatus.PROPOSAL.value:
        raise PrototypeError("Замечания можно отправить только по отправленному КП")
    workflow = ensure_workflow(db, order)
    workflow.remarks = payload.text.strip()
    change_status(
        db,
        order,
        OrderStatus.REVISION.value,
        actor_type=ActorType.SYSTEM.value,
        comment="Получены замечания",
        notify=False,
    )
    notify_managers(db, order, "Замечания клиента по КП")
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def form_contract(db: Session, order: Order) -> PrototypeOrderOut:
    workflow = ensure_workflow(db, order)
    signed = (
        workflow.signed_at is not None
        or any(
            doc.doc_type == DocumentType.PROPOSAL.value and doc.status == "signed"
            for doc in order.documents
        )
        or order.status
        in {
            OrderStatus.APPROVED.value,
            OrderStatus.CONTRACT.value,
            OrderStatus.IN_PROGRESS.value,
            OrderStatus.DONE.value,
        }
    )
    if not signed:
        raise PrototypeError("Сначала подпишите КП")
    if order.status == OrderStatus.APPROVED.value:
        change_status(
            db,
            order,
            OrderStatus.CONTRACT.value,
            actor_type=ActorType.SYSTEM.value,
            comment="Договор сформирован",
        )
        order = _load_order(db, order.id) or order
    elif order.status not in {
        OrderStatus.CONTRACT.value,
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.DONE.value,
    }:
        raise PrototypeError("Договор можно сформировать после подписания КП")
    workflow = ensure_workflow(db, order)
    workflow.contract_at = workflow.contract_at or utcnow()
    created = False
    if not any(
        doc.doc_type == DocumentType.CONTRACT.value for doc in order.documents
    ):
        create_document_record(db, order, DocumentType.CONTRACT.value)
        created = True
    if created and order.status != OrderStatus.CONTRACT.value:
        notify_client(
            db,
            order,
            "Договор готов",
            document_type=DocumentType.CONTRACT.value,
        )
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def start_work(db: Session, order: Order) -> PrototypeOrderOut:
    if order.status == OrderStatus.CONTRACT.value:
        change_status(
            db,
            order,
            OrderStatus.IN_PROGRESS.value,
            actor_type=ActorType.SYSTEM.value,
            comment="Работа начата",
        )
        order = _load_order(db, order.id) or order
    elif order.status not in {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.DONE.value,
    }:
        raise PrototypeError("Сначала сформируйте договор")
    workflow = ensure_workflow(db, order)
    workflow.work_started_at = workflow.work_started_at or utcnow()
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def form_act(db: Session, order: Order) -> PrototypeOrderOut:
    if order.status not in {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.DONE.value,
    }:
        raise PrototypeError("Акт формируется только после начала работы")
    workflow = ensure_workflow(db, order)
    created = False
    if not any(doc.doc_type == DocumentType.ACT.value for doc in order.documents):
        create_document_record(db, order, DocumentType.ACT.value)
        order = _load_order(db, order.id) or order
        workflow = ensure_workflow(db, order)
        created = True
    workflow.act_at = workflow.act_at or utcnow()
    if created:
        notify_client(
            db,
            order,
            "Акт готов к подтверждению",
            document_type=DocumentType.ACT.value,
        )
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def confirm_act(db: Session, order: Order) -> PrototypeOrderOut:
    acts = [doc for doc in order.documents if doc.doc_type == DocumentType.ACT.value]
    if not acts:
        raise PrototypeError("Акт ещё не сформирован")
    if order.status == OrderStatus.IN_PROGRESS.value:
        change_status(
            db,
            order,
            OrderStatus.DONE.value,
            actor_type=ActorType.SYSTEM.value,
            comment="Акт подтверждён, заказ завершён",
            create_documents=False,
            notify=False,
        )
        order = _load_order(db, order.id) or order
        acts = [
            doc for doc in order.documents if doc.doc_type == DocumentType.ACT.value
        ]
    elif order.status != OrderStatus.DONE.value:
        raise PrototypeError("Подтвердить акт можно только после начала работы")
    acts.sort(key=lambda doc: doc.created_at or utcnow())
    acts[-1].status = "signed"
    workflow = ensure_workflow(db, order)
    workflow.act_confirmed_at = workflow.act_confirmed_at or utcnow()
    notify_managers(db, order, "Клиент подтвердил акт")
    db.commit()
    return serialize_order(db, _load_order(db, order.id) or order)


def pay_order(
    db: Session, order: Order, payload: PrototypePaymentIn
) -> PrototypeOrderOut:
    workflow = ensure_workflow(db, order)
    signed = (
        workflow.signed_at is not None
        or any(
            doc.doc_type == DocumentType.PROPOSAL.value and doc.status == "signed"
            for doc in order.documents
        )
        or order.status
        in {
            OrderStatus.APPROVED.value,
            OrderStatus.CONTRACT.value,
            OrderStatus.IN_PROGRESS.value,
            OrderStatus.DONE.value,
        }
    )
    if not signed:
        raise PrototypeError("Сначала подпишите КП")

    amount = to_money(order.amount or 0)
    if amount <= 0:
        raise PrototypeError("В заявке не указана стоимость")
    already_paid = any(
        doc.doc_type == DocumentType.PAYMENT.value and doc.status == "paid"
        for doc in order.documents
    ) or to_money(order.paid_amount or 0) >= amount
    if already_paid:
        raise PrototypeError("Заявка уже оплачена")

    digits = re.sub(r"\D", "", payload.card_number)
    if len(digits) != 16:
        raise PrototypeError("Номер тестовой карты должен содержать 16 цифр")
    if digits == "4000000000000002":
        raise PrototypeError("Банк отклонил тестовую оплату")

    expiry_match = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2})", payload.expiry.strip())
    if not expiry_match:
        raise PrototypeError("Срок действия укажите в формате ММ/ГГ")
    month = int(expiry_match.group(1))
    year = 2000 + int(expiry_match.group(2))
    today = utcnow()
    if (year, month) < (today.year, today.month):
        raise PrototypeError("Срок действия карты уже истёк")
    if not re.fullmatch(r"\d{3}", payload.cvc):
        raise PrototypeError("CVC должен содержать 3 цифры")

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
        "last4": digits[-4:],
        "amount": format_money(amount),
        "test": True,
    }
    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=order.status,
            to_status=order.status,
            actor_type=ActorType.USER.value,
            comment=(
                f"Тестовая оплата {format_money(amount)} "
                f"— карта •••• {digits[-4:]}"
            ),
        )
    )
    notify_managers(db, order, "Клиент оплатил заявку (тестовый платёж)")
    db.commit()
    db.refresh(order)
    return serialize_order(db, _load_order(db, order.id) or order)


__all__ = [
    "DEMO_CLIENT_NAME",
    "DEMO_BOT_TELEGRAM_ID",
    "PROTOTYPE_CONSULTANTS",
    "DEFAULT_FILE",
    "DEFAULT_SLA",
    "PrototypeError",
    "bootstrap",
    "confirm_act",
    "create_prototype_order",
    "demo_orders",
    "ensure_workflow",
    "form_act",
    "form_contract",
    "get_order",
    "is_demo_order",
    "next_display_number",
    "pay_order",
    "prototype_status",
    "request_clarification",
    "send_proposal",
    "serialize_order",
    "sign_proposal",
    "start_work",
    "submit_answer",
    "submit_remarks",
    "update_practice",
]
