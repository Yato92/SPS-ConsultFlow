"""Клиенты ConsultFlow."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Client, Order, User
from app.schemas import ClientCreate, ClientListOut, ClientOut, ClientStatsOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ClientListOut)
def list_clients(
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClientListOut:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Client.name.ilike(pattern),
                Client.contact_person.ilike(pattern),
                Client.email.ilike(pattern),
                Client.phone.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count(Client.id)).where(*filters)) or 0
    clients = list(
        db.scalars(
            select(Client)
            .where(*filters)
            .order_by(Client.name)
            .offset(offset)
            .limit(limit)
        ).all()
    )

    stats: dict[int, tuple[int, float, float]] = {}
    if clients:
        ids = [client.id for client in clients]
        rows = db.execute(
            select(
                Order.client_id,
                func.count(Order.id),
                func.coalesce(func.sum(Order.paid_amount), 0),
                func.coalesce(func.sum(Order.expenses), 0),
            )
            .where(Order.client_id.in_(ids), Order.is_deleted.is_(False))
            .group_by(Order.client_id)
        ).all()
        for client_id, orders_count, paid, expenses in rows:
            stats[client_id] = (int(orders_count), float(paid or 0), float(paid or 0) - float(expenses or 0))

    items = []
    for client in clients:
        orders_count, paid_total, profit = stats.get(client.id, (0, 0.0, 0.0))
        items.append(
            ClientStatsOut(
                **ClientOut.model_validate(client).model_dump(),
                orders_count=orders_count,
                paid_total=round(paid_total, 2),
                profit=round(profit, 2),
            )
        )

    return ClientListOut(items=items, total=total)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClientOut:
    client = Client(
        name=payload.name.strip(),
        inn=payload.inn,
        contact_person=payload.contact_person,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        telegram_id=payload.telegram_id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClientOut:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return ClientOut.model_validate(client)
