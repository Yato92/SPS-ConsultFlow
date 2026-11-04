"""Общие утилиты: время, деньги, номера заказов."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


def utcnow() -> datetime:
    """Наивное UTC-время — одинаково хранится в SQLite и PostgreSQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_money(value: float | int | Decimal | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_money(value: Decimal | float | int | None) -> str:
    amount = money_float(value)
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",") + " ₽"
