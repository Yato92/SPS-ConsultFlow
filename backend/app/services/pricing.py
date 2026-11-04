"""Прайс-лист и расчёт стоимости консалтинговых услуг."""

from app.core.enums import PRACTICE_LABELS, Practice
from app.core.utils import to_money

# Ставка консультанта, ₽/час, по направлению практики.
PRACTICE_RATES: dict[str, float] = {
    Practice.MANAGEMENT.value: 4500.0,
    Practice.FINANCE.value: 5000.0,
    Practice.LEGAL.value: 5500.0,
    Practice.IT.value: 6000.0,
}

# Нормативный срок первичной обработки заявки (SLA), часы.
SLA_HOURS: dict[str, int] = {
    Practice.MANAGEMENT.value: 48,
    Practice.FINANCE.value: 24,
    Practice.LEGAL.value: 72,
    Practice.IT.value: 48,
}

# Коэффициенты сложности проекта.
COMPLEXITY: dict[str, tuple[str, float]] = {
    "basic": ("Базовая", 1.0),
    "standard": ("Стандартная", 1.25),
    "complex": ("Сложная", 1.6),
}


def get_rate(practice: str) -> float:
    return PRACTICE_RATES.get(practice, PRACTICE_RATES[Practice.MANAGEMENT.value])


def get_sla_hours(practice: str) -> int:
    return SLA_HOURS.get(practice, 48)


def estimate(
    practice: str,
    hours: float,
    complexity: str = "standard",
) -> dict[str, float | int | str]:
    """Предварительная оценка стоимости и SLA по параметрам заявки."""
    multiplier = COMPLEXITY.get(complexity, COMPLEXITY["standard"])[1]
    rate = get_rate(practice)
    amount = to_money(rate * max(hours, 1) * multiplier)
    return {
        "practice": practice,
        "practice_label": PRACTICE_LABELS.get(practice, practice),
        "rate": rate,
        "hours": float(hours),
        "complexity": complexity,
        "complexity_label": COMPLEXITY.get(complexity, COMPLEXITY["standard"])[0],
        "multiplier": multiplier,
        "amount": float(amount),
        "sla_hours": get_sla_hours(practice),
    }


def pricing_info() -> dict:
    return {
        "practices": [
            {
                "value": value,
                "label": PRACTICE_LABELS[value],
                "rate": PRACTICE_RATES[value],
                "sla_hours": SLA_HOURS[value],
            }
            for value in PRACTICE_RATES
        ],
        "complexities": [
            {"value": key, "label": label, "multiplier": multiplier}
            for key, (label, multiplier) in COMPLEXITY.items()
        ],
    }
