"""Аналитика и агрегаты для дашборда."""

from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import (
    ACTIVE_STATUSES,
    PRACTICE_LABELS,
    STATUS_LABELS,
    OrderStatus,
    Practice,
)
from app.core.utils import utcnow
from app.models import Order
from app.schemas import (
    DashboardOut,
    ManagerStat,
    MonthlyPoint,
    OrderOut,
    PracticeStat,
    StatusStat,
    SummaryOut,
)

MONTHS_RU = [
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
]

STATUS_ORDER = [status.value for status in OrderStatus]


def _f(value: Decimal | float | None) -> float:
    return float(value or 0)


def _month_keys(count: int = 12) -> list[tuple[str, str]]:
    now = utcnow()
    keys: list[tuple[str, str]] = []
    year, month = now.year, now.month
    for _ in range(count):
        keys.append((f"{year:04d}-{month:02d}", f"{MONTHS_RU[month - 1]} {year}"))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(keys))


def _base_query(date_from: date | None, date_to: date | None, practice: str | None):
    query = select(Order).options(
        selectinload(Order.client), selectinload(Order.manager)
    )
    if date_from:
        query = query.where(Order.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(Order.created_at <= datetime.combine(date_to, time.max))
    if practice:
        query = query.where(Order.practice == practice)
    return query.order_by(Order.created_at.desc())


def build_dashboard(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    practice: str | None = None,
) -> DashboardOut:
    orders = list(db.scalars(_base_query(date_from, date_to, practice)).all())

    total = len(orders)
    amount_total = sum(_f(order.amount) for order in orders)
    paid_total = sum(_f(order.paid_amount) for order in orders)
    expenses_total = sum(_f(order.expenses) for order in orders)
    profit = paid_total - expenses_total
    closed = [order for order in orders if order.status == OrderStatus.CLOSED.value]
    active = [order for order in orders if order.status in ACTIVE_STATUSES]
    overdue = [order for order in orders if order.is_overdue]

    cycles = [
        (order.closed_at - order.created_at).total_seconds() / 86400
        for order in closed
        if order.closed_at and order.created_at
    ]

    summary = SummaryOut(
        orders_total=total,
        active_orders=len(active),
        closed_orders=len(closed),
        amount_total=round(amount_total, 2),
        paid_total=round(paid_total, 2),
        expenses_total=round(expenses_total, 2),
        profit=round(profit, 2),
        avg_check=round(amount_total / total, 2) if total else 0,
        conversion=round(len(closed) / total * 100, 1) if total else 0,
        overdue_count=len(overdue),
        avg_cycle_days=round(sum(cycles) / len(cycles), 1) if cycles else 0,
    )

    # Помесячная динамика за последние 12 месяцев.
    buckets: dict[str, dict[str, float]] = {
        key: {"orders": 0, "paid": 0.0, "expenses": 0.0, "profit": 0.0}
        for key, _ in _month_keys()
    }
    for order in orders:
        key = order.created_at.strftime("%Y-%m")
        if key in buckets:
            bucket = buckets[key]
            bucket["orders"] += 1
            bucket["paid"] += _f(order.paid_amount)
            bucket["expenses"] += _f(order.expenses)
            bucket["profit"] += _f(order.paid_amount) - _f(order.expenses)

    monthly = [
        MonthlyPoint(
            month=key,
            label=label,
            orders=int(buckets[key]["orders"]),
            paid=round(buckets[key]["paid"], 2),
            expenses=round(buckets[key]["expenses"], 2),
            profit=round(buckets[key]["profit"], 2),
        )
        for key, label in _month_keys()
    ]

    # Разрез по направлениям консалтинга.
    by_practice_acc: dict[str, dict[str, float]] = {
        item.value: {"orders": 0, "amount": 0.0, "paid": 0.0, "expenses": 0.0}
        for item in Practice
    }
    for order in orders:
        acc = by_practice_acc.setdefault(
            order.practice,
            {"orders": 0, "amount": 0.0, "paid": 0.0, "expenses": 0.0},
        )
        acc["orders"] += 1
        acc["amount"] += _f(order.amount)
        acc["paid"] += _f(order.paid_amount)
        acc["expenses"] += _f(order.expenses)

    by_practice = [
        PracticeStat(
            practice=key,
            label=PRACTICE_LABELS.get(key, key),
            orders=int(value["orders"]),
            amount=round(value["amount"], 2),
            paid=round(value["paid"], 2),
            expenses=round(value["expenses"], 2),
            profit=round(value["paid"] - value["expenses"], 2),
        )
        for key, value in by_practice_acc.items()
    ]

    # Распределение по статусам.
    status_acc: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0, "amount": 0.0}
    )
    for order in orders:
        status_acc[order.status]["count"] += 1
        status_acc[order.status]["amount"] += _f(order.amount)

    by_status = [
        StatusStat(
            status=key,
            label=STATUS_LABELS.get(key, key),
            count=int(status_acc[key]["count"]),
            amount=round(status_acc[key]["amount"], 2),
        )
        for key in STATUS_ORDER
        if key in status_acc
    ]

    # Эффективность менеджеров.
    manager_acc: dict[int | None, dict] = {}
    for order in orders:
        acc = manager_acc.setdefault(
            order.manager_id,
            {"name": order.manager.full_name if order.manager else "Не назначен", "orders": 0, "paid": 0.0, "profit": 0.0},
        )
        acc["orders"] += 1
        acc["paid"] += _f(order.paid_amount)
        acc["profit"] += _f(order.paid_amount) - _f(order.expenses)

    managers = [
        ManagerStat(
            manager_id=manager_id,
            name=value["name"],
            orders=int(value["orders"]),
            paid=round(value["paid"], 2),
            profit=round(value["profit"], 2),
        )
        for manager_id, value in sorted(
            manager_acc.items(), key=lambda item: item[1]["paid"], reverse=True
        )
    ]

    recent = [OrderOut.model_validate(order) for order in orders[:6]]
    overdue_orders = [
        OrderOut.model_validate(order)
        for order in sorted(overdue, key=lambda item: item.sla_due_at or utcnow())[:6]
    ]

    return DashboardOut(
        summary=summary,
        monthly=monthly,
        by_practice=by_practice,
        by_status=by_status,
        managers=managers,
        recent_orders=recent,
        overdue_orders=overdue_orders,
        generated_at=utcnow(),
    )
