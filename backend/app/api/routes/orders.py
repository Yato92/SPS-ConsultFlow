"""Заказы ConsultFlow: список, карточка, статусы, документы."""

import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import MANAGER_ROLES, get_current_user, require_roles
from app.core.enums import (
    PRACTICE_LABELS,
    STATUS_LABELS,
    ActorType,
    OrderStatus,
    Practice,
    UserRole,
)
from app.core.utils import utcnow
from app.db.session import get_db
from app.models import Client, Document, Order, User
from app.schemas import (
    DocumentCreate,
    DocumentOut,
    OrderCreate,
    OrderDetailOut,
    OrderListOut,
    OrderOut,
    OrderUpdate,
    StatusChangeIn,
)
from app.services.orders import change_status, create_document_record, create_order, update_order_fields

router = APIRouter(prefix="/orders", tags=["orders"])

SORT_COLUMNS = {
    "created_at": Order.created_at,
    "updated_at": Order.updated_at,
    "amount": Order.amount,
    "paid_amount": Order.paid_amount,
    "number": Order.number,
    "deadline": Order.deadline,
    "status": Order.status,
}


def _get_order(db: Session, order_id: int, *, include_deleted: bool = False) -> Order:
    query = select(Order).where(Order.id == order_id)
    if not include_deleted:
        query = query.where(Order.is_deleted.is_(False))
    order = db.scalar(
        query.options(
            selectinload(Order.client),
            selectinload(Order.manager),
            selectinload(Order.events),
            selectinload(Order.documents),
        )
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.get("", response_model=OrderListOut)
def list_orders(
    q: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    practice: str | None = None,
    manager_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort_by: str = "created_at",
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    include_deleted: bool = Query(
        default=False, description="Показать удалённые заявки (архив)"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderListOut:
    filters = []
    join_client = False

    if include_deleted and user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=403, detail="Архив доступен только сотрудникам"
        )
    if not include_deleted:
        filters.append(Order.is_deleted.is_(False))

    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Order.number.ilike(pattern),
                Order.title.ilike(pattern),
                Client.name.ilike(pattern),
            )
        )
        join_client = True
    if status_filter:
        statuses = [item.strip() for item in status_filter.split(",") if item.strip()]
        if statuses:
            filters.append(Order.status.in_(statuses))
    if practice:
        filters.append(Order.practice == practice)
    if manager_id is not None:
        filters.append(Order.manager_id == manager_id)
    if date_from:
        filters.append(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        filters.append(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    count_query = select(func.count(Order.id))
    if join_client:
        count_query = count_query.join(Order.client)
    total = db.scalar(count_query.where(*filters)) or 0

    query = select(Order).options(
        selectinload(Order.client), selectinload(Order.manager)
    )
    if join_client:
        query = query.join(Order.client)
    column = SORT_COLUMNS.get(sort_by, Order.created_at)
    query = (
        query.where(*filters)
        .order_by(column.desc() if sort_dir == "desc" else column.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = list(db.scalars(query).all())

    return OrderListOut(
        items=[OrderOut.model_validate(order) for order in orders],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/export/csv")
def export_orders_csv(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*MANAGER_ROLES)),
) -> StreamingResponse:
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.is_deleted.is_(False))
            .options(selectinload(Order.client), selectinload(Order.manager))
            .order_by(Order.created_at.desc())
        ).all()
    )
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "Номер",
            "Дата",
            "Клиент",
            "Направление",
            "Менеджер",
            "Статус",
            "Стоимость",
            "Оплачено",
            "Расходы",
            "Результат",
            "Источник",
        ]
    )
    for order in orders:
        writer.writerow(
            [
                order.number,
                order.created_at.strftime("%d.%m.%Y"),
                order.client.name if order.client else "",
                PRACTICE_LABELS.get(order.practice, order.practice),
                order.manager.full_name if order.manager else "",
                STATUS_LABELS.get(order.status, order.status),
                f"{float(order.amount):.2f}",
                f"{float(order.paid_amount):.2f}",
                f"{float(order.expenses):.2f}",
                f"{float(order.paid_amount) - float(order.expenses):.2f}",
                order.source,
            ]
        )
    buffer.seek(0)
    filename = f"consultflow-orders-{datetime.now():%Y%m%d}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> OrderOut:
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    manager_id = payload.manager_id or user.id
    manager = db.get(User, manager_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Менеджер не найден")

    order = create_order(
        db,
        client=client,
        practice=payload.practice.value,
        title=payload.title,
        description=payload.description,
        manager_id=manager_id,
        amount=payload.amount,
        deadline=payload.deadline,
        source="dashboard",
        actor_type=ActorType.USER.value,
        actor_id=user.id,
    )
    db.refresh(order, ["client", "manager"])
    return OrderOut.model_validate(order)


@router.get("/{order_id}", response_model=OrderDetailOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> OrderDetailOut:
    return OrderDetailOut.model_validate(_get_order(db, order_id))


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> OrderOut:
    order = _get_order(db, order_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "practice" in data and data["practice"] is not None:
        data["practice"] = Practice(data["practice"]).value
    if "manager_id" in data and db.get(User, data["manager_id"]) is None:
        raise HTTPException(status_code=404, detail="Менеджер не найден")
    order = update_order_fields(db, order, data, actor_id=user.id)
    db.refresh(order, ["client", "manager"])
    return OrderOut.model_validate(order)


@router.post("/{order_id}/restore", response_model=OrderOut)
def restore_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> OrderOut:
    """Возвращает удалённую заявку из архива."""
    from app.services.orders import audit

    order = _get_order(db, order_id, include_deleted=True)
    if not order.is_deleted:
        raise HTTPException(status_code=400, detail="Заявка не удалена")
    order.is_deleted = False
    order.deleted_at = None
    order.deleted_by = None
    order.updated_at = utcnow()
    audit(
        db,
        "order.restored",
        actor_type=ActorType.USER.value,
        actor_id=user.id,
        entity="order",
        entity_id=order.id,
    )
    db.commit()
    db.refresh(order, ["client", "manager"])
    return OrderOut.model_validate(order)


@router.delete("/{order_id}", response_model=OrderOut)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> OrderOut:
    """Мягкое удаление: заявка скрывается, но остаётся в базе."""
    from app.services.orders import audit

    order = _get_order(db, order_id)
    order.is_deleted = True
    order.deleted_at = utcnow()
    order.deleted_by = user.id
    order.updated_at = utcnow()
    audit(
        db,
        "order.soft_deleted",
        actor_type=ActorType.USER.value,
        actor_id=user.id,
        entity="order",
        entity_id=order.id,
        meta={"number": order.number},
    )
    db.commit()
    db.refresh(order, ["client", "manager"])
    return OrderOut.model_validate(order)


@router.post("/{order_id}/status", response_model=OrderDetailOut)
def set_status(
    order_id: int,
    payload: StatusChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderDetailOut:
    order = _get_order(db, order_id)
    try:
        change_status(
            db,
            order,
            payload.status.value,
            actor_type=ActorType.USER.value,
            actor_id=user.id,
            comment=payload.comment,
            force=user.role == UserRole.ADMIN.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OrderDetailOut.model_validate(_get_order(db, order_id))


@router.post(
    "/{order_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_document(
    order_id: int,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> DocumentOut:
    order = _get_order(db, order_id)
    document = create_document_record(
        db,
        order,
        payload.doc_type.value,
        actor_type=ActorType.USER.value,
        actor_id=user.id,
    )
    return DocumentOut.model_validate(document)


@router.post("/{order_id}/documents/{document_id}/sign", response_model=DocumentOut)
def sign_document(
    order_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None or document.order_id != order_id:
        raise HTTPException(status_code=404, detail="Документ не найден")
    document.status = "signed"
    from app.services.orders import audit

    audit(
        db,
        "document.signed",
        actor_type=ActorType.USER.value,
        actor_id=user.id,
        entity="document",
        entity_id=document.id,
        meta={"number": document.number},
    )
    db.commit()
    db.refresh(document)
    return DocumentOut.model_validate(document)
