# -*- coding: utf-8 -*-
r"""Генератор воспроизводимого CSV с тестовыми заказами ConsultFlow.

100 вымышленных заказов за 2025 год. Данные предназначены только для
учебного дашборда и не являются реальными сведениями о клиентах.

Запуск из корня репозитория:
    .\.venv\Scripts\python.exe dashboard\generate_orders.py
"""

from __future__ import annotations

import csv
import random
from datetime import date
from pathlib import Path

RANDOM_SEED = 42
YEAR = 2025
ORDERS_COUNT = 100
OUTPUT_PATH = Path(__file__).with_name("orders.csv")

PRACTICES = {
    "Управленческий консалтинг": (120_000, 900_000),
    "Финансовый консалтинг": (150_000, 1_100_000),
    "Юридический консалтинг": (90_000, 700_000),
    "IT-консалтинг": (200_000, 1_500_000),
}

MANAGERS = [
    "Анна Смирнова",
    "Дмитрий Орлов",
    "Елена Ковалёва",
    "Игорь Лебедев",
    "Мария Соколова",
]

CLIENTS = [
    "ООО «Вектор»",
    "ООО «Северный мост»",
    "АО «Гранит-Строй»",
    "ООО «Лазурит»",
    "ООО «ТехноПарк»",
    "АО «МедСервис»",
    "ООО «АгроПром»",
    "ООО «Логистика Плюс»",
    "АО «ЭнергоСеть»",
    "ООО «Ритейл Групп»",
    "ООО «СтройКонтур»",
    "АО «ФинТраст»",
    "ООО «ДатаЛаб»",
    "ООО «ЭкоСистемы»",
    "АО «Машиностроитель»",
    "ООО «Гостиный двор»",
    "ООО «МедиаКварц»",
    "АО «ТеплоЭнерго»",
    "ООО «Кадровый центр»",
    "ООО «БиоФарм»",
]

# Статус: (доля полученной оплаты, диапазон доли расходов, вес в наборе).
# Полная предоплата принята для заказов в работе и завершённых заказов.
# До начала работ расходы по заказу не учитываются; у отклонённых заказов
# остаются только затраты на предпроектную проработку.
STATUS_RULES = {
    "Заявка зарегистрирована": (0.0, (0.00, 0.00), 6),
    "Проверка данных": (0.0, (0.00, 0.00), 6),
    "Подготовка КП": (0.0, (0.00, 0.00), 8),
    "Согласование КП": (0.0, (0.00, 0.00), 8),
    "Ожидает оплаты": (0.0, (0.00, 0.00), 12),
    "В работе": (1.0, (0.35, 0.60), 14),
    "Акт подписан": (1.0, (0.50, 0.72), 10),
    "Завершён": (1.0, (0.50, 0.75), 32),
    "Отклонён": (0.0, (0.02, 0.04), 4),
}

# Заказы, которые специально сделаны убыточными: переработка и
# непредвиденные расходы исполнителя. Это объясняет отрицательный
# учебный финансовый результат у части завершённых заказов.
LOSS_ORDERS = 4

COLUMNS = [
    "order_id",
    "created_date",
    "client",
    "practice",
    "manager",
    "status",
    "amount",
    "paid_amount",
    "expenses",
]


def weighted_statuses() -> list[str]:
    """Список статусов с повторами согласно весам."""
    statuses = []
    for status, (_, _, weight) in STATUS_RULES.items():
        statuses.extend([status] * weight)
    return statuses


def build_orders() -> list[dict]:
    """Сформировать 100 заказов с согласованными суммами."""
    rng = random.Random(RANDOM_SEED)
    status_pool = weighted_statuses()

    # Месяц задаётся по кругу, поэтому в наборе гарантированно есть все
    # 12 месяцев 2025 года.
    raw_dates = [
        (date(YEAR, index % 12 + 1, rng.randint(1, 28)), index)
        for index in range(ORDERS_COUNT)
    ]
    raw_dates.sort()

    orders = []
    for order_number, (created_date, _) in enumerate(raw_dates, start=1):
        practice = rng.choice(list(PRACTICES))
        amount_min, amount_max = PRACTICES[practice]
        amount = rng.randrange(amount_min, amount_max + 1, 1_000)
        status = rng.choice(status_pool)
        paid_ratio, expense_range, _ = STATUS_RULES[status]
        expenses = round(amount * rng.uniform(*expense_range), -3)

        orders.append(
            {
                "order_id": f"CF-{YEAR}-{order_number:03d}",
                "created_date": created_date.isoformat(),
                "client": rng.choice(CLIENTS),
                "practice": practice,
                "manager": rng.choice(MANAGERS),
                "status": status,
                "amount": amount,
                "paid_amount": int(round(amount * paid_ratio)),
                "expenses": int(expenses),
            }
        )

    # Несколько завершённых заказов с расходами больше оплаты.
    completed = [
        index
        for index, order in enumerate(orders)
        if order["status"] in {"Завершён", "Акт подписан"}
    ]
    for index in rng.sample(completed, LOSS_ORDERS):
        orders[index]["expenses"] = int(
            round(orders[index]["amount"] * rng.uniform(1.05, 1.15), -3)
        )

    return orders


def write_csv(orders: list[dict]) -> None:
    """Записать CSV в UTF-8 с BOM, чтобы файл корректно открывался в Excel."""
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(orders)


def main() -> None:
    orders = build_orders()
    write_csv(orders)
    total_paid = sum(order["paid_amount"] for order in orders)
    total_expenses = sum(order["expenses"] for order in orders)
    losses = sum(
        1
        for order in orders
        if order["paid_amount"] - order["expenses"] < 0
    )
    print(f"Файл: {OUTPUT_PATH}")
    print(f"Заказов: {len(orders)}")
    print(f"Период: {orders[0]['created_date']} — {orders[-1]['created_date']}")
    print(f"Полученная оплата: {total_paid:,} ₽".replace(",", " "))
    print(f"Расходы: {total_expenses:,} ₽".replace(",", " "))
    print(f"Убыточных заказов: {losses}")


if __name__ == "__main__":
    main()
