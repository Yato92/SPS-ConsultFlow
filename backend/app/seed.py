"""Демонстрационные данные ConsultFlow (идемпотентно)."""

import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    BotRole,
    DocumentType,
    OrderStatus,
    Practice,
    UserRole,
)
from app.core.security import hash_password
from app.core.utils import to_money, utcnow
from app.models import BotUser, Client, Document, Order, OrderEvent, User
from app.services.documents import build_document
from app.services.pricing import estimate, get_sla_hours

CLIENTS = [
    ("ООО «Дальневосточная логистика»", "Дальневосточная логистика", "Иванов Артём Сергеевич", "logistics@example.ru", "+7 (4212) 45-12-01"),
    ("АО «Амурметалл»", "Амурметалл", "Петрова Мария Викторовна", "amur@example.ru", "+7 (4217) 32-18-44"),
    ("ООО «ТехноПарк»", "ТехноПарк", "Соколов Дмитрий Игоревич", "technopark@example.ru", "+7 (4212) 77-30-15"),
    ("ПАО «Банк Приморья»", "Банк Приморья", "Ковалёва Ольга Андреевна", "bank@example.ru", "+7 (423) 26-55-90"),
    ("ООО «МедСервис»", "МедСервис", "Орлов Никита Павлович", "medservice@example.ru", "+7 (4212) 51-08-33"),
    ("ГК «СтройИнвест»", "СтройИнвест", "Фёдорова Елена Алексеевна", "stroyinvest@example.ru", "+7 (4212) 63-21-70"),
    ("ООО «АгроТрейд»", "АгроТрейд", "Морозов Сергей Владимирович", "agrotrade@example.ru", "+7 (4162) 22-44-18"),
    ("ООО «Цифровые решения»", "Цифровые решения", "Волкова Анна Дмитриевна", "digital@example.ru", "+7 (4212) 90-12-55"),
    ("АО «Хабаровскэнерго»", "Хабаровскэнерго", "Лебедев Павел Олегович", "energy@example.ru", "+7 (4212) 38-76-20"),
    ("ООО «Ритейл Плюс»", "Ритейл Плюс", "Никитина Светлана Игоревна", "retail@example.ru", "+7 (4212) 55-67-89"),
]

TITLES = {
    Practice.MANAGEMENT.value: [
        "Разработка стратегии развития на 2026–2028 годы",
        "Оптимизация организационной структуры",
        "Аудит бизнес-процессов и подготовка карты процессов",
        "Программа повышения операционной эффективности",
    ],
    Practice.FINANCE.value: [
        "Финансовое моделирование инвестиционного проекта",
        "Постановка управленческого учёта",
        "Оценка инвестиционной привлекательности бизнеса",
        "Бюджетирование подразделений и центров затрат",
    ],
    Practice.LEGAL.value: [
        "Правовая экспертиза договорного портфеля",
        "Сопровождение сделки по приобретению актива",
        "Регистрация прав на интеллектуальную собственность",
        "Комплаенс-аудит и оценка регуляторных рисков",
    ],
    Practice.IT.value: [
        "Аудит ИТ-инфраструктуры и разработка целевой архитектуры",
        "Проектирование интеграционной платформы",
        "Внедрение BI-отчётности для руководства",
        "План миграции информационных систем в облако",
    ],
}

DESCRIPTIONS = [
    "Клиенту требуется независимая экспертиза и практические рекомендации по развитию направления.",
    "Проект включает диагностику, интервью с ключевыми сотрудниками и подготовку итогового отчёта.",
    "Основная задача — снизить издержки и повысить прозрачность ключевых показателей.",
    "Работы выполняются поэтапно: сбор данных, анализ, разработка рекомендаций, презентация результатов.",
]

STATUS_WEIGHTS = [
    (OrderStatus.NEW.value, 8),
    (OrderStatus.QUALIFIED.value, 9),
    (OrderStatus.PROPOSAL.value, 11),
    (OrderStatus.APPROVED.value, 8),
    (OrderStatus.CONTRACT.value, 8),
    (OrderStatus.IN_PROGRESS.value, 14),
    (OrderStatus.DONE.value, 10),
    (OrderStatus.CLOSED.value, 24),
    (OrderStatus.CANCELLED.value, 8),
]

STATUS_PATH = [
    OrderStatus.NEW.value,
    OrderStatus.QUALIFIED.value,
    OrderStatus.PROPOSAL.value,
    OrderStatus.APPROVED.value,
    OrderStatus.CONTRACT.value,
    OrderStatus.IN_PROGRESS.value,
    OrderStatus.DONE.value,
    OrderStatus.CLOSED.value,
]


def _pick_status(rng: random.Random) -> str:
    population = [item[0] for item in STATUS_WEIGHTS]
    weights = [item[1] for item in STATUS_WEIGHTS]
    return rng.choices(population, weights=weights, k=1)[0]


def seed(db: Session, *, force: bool = False) -> bool:
    settings = get_settings()
    if db.scalar(select(User).limit(1)) is not None and not force:
        return False

    now = utcnow()
    rng = random.Random(42)

    admin = User(
        email=settings.admin_email.lower(),
        full_name="Иванов Иван Сергеевич",
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN.value,
        telegram_id=next(iter(settings.manager_ids), None),
    )
    manager = User(
        email="manager@consultflow.ru",
        full_name="Петров Пётр Алексеевич",
        password_hash=hash_password("manager12345"),
        role=UserRole.MANAGER.value,
    )
    consultant = User(
        email="consultant@consultflow.ru",
        full_name="Сидорова Светлана Игоревна",
        password_hash=hash_password("consultant12345"),
        role=UserRole.CONSULTANT.value,
    )
    lawyer = User(
        email="lawyer@consultflow.ru",
        full_name="Кузнецов Кирилл Олегович",
        password_hash=hash_password("lawyer12345"),
        role=UserRole.LAWYER.value,
    )
    finance = User(
        email="finance@consultflow.ru",
        full_name="Смирнова Анна Павловна",
        password_hash=hash_password("finance12345"),
        role=UserRole.FINANCE.value,
    )
    db.add_all([admin, manager, consultant, lawyer, finance])
    db.flush()

    staff = [admin, manager]
    clients: list[Client] = []
    for name, short, contact, email, phone in CLIENTS:
        client = Client(
            name=name,
            inn=f"{rng.randint(10**9, 10**10 - 1)}",
            contact_person=contact,
            email=email,
            phone=phone,
        )
        db.add(client)
        clients.append(client)
    db.flush()

    # Клиент, который пользуется Telegram-ботом.
    bot_client = BotUser(
        telegram_id=700000001,
        username="demo_client",
        full_name="Смирнов Алексей Владимирович",
        phone="+7 (914) 123-45-67",
        email="client@example.ru",
        role=BotRole.CLIENT.value,
    )
    bot_manager = BotUser(
        telegram_id=700000002,
        username="demo_manager",
        full_name=manager.full_name,
        role=BotRole.MANAGER.value,
        user_id=manager.id,
    )
    db.add_all([bot_client, bot_manager])
    db.flush()

    clients[0].telegram_id = bot_client.telegram_id

    year_counters: dict[int, int] = {}
    orders: list[Order] = []

    for _ in range(72):
        created_at = now - timedelta(
            days=rng.randint(0, 360),
            hours=rng.randint(8, 19),
            minutes=rng.randint(0, 59),
        )
        practice = rng.choice(list(Practice)).value
        status_value = _pick_status(rng)
        if (now - created_at).days < 7 and status_value not in {
            OrderStatus.NEW.value,
            OrderStatus.QUALIFIED.value,
            OrderStatus.PROPOSAL.value,
        }:
            status_value = OrderStatus.NEW.value

        hours = rng.choice([12, 20, 24, 32, 40, 48, 60, 80, 96, 120])
        complexity = rng.choice(["basic", "standard", "standard", "complex"])
        calc = estimate(practice, hours, complexity)
        amount = to_money(calc["amount"])

        if status_value == OrderStatus.CLOSED.value:
            paid = amount
            expenses = to_money(float(amount) * rng.uniform(0.34, 0.58))
            closed_at = created_at + timedelta(days=rng.randint(12, 55))
            if closed_at > now:
                closed_at = now - timedelta(days=1)
        elif status_value == OrderStatus.DONE.value:
            paid = to_money(float(amount) * rng.uniform(0.55, 0.95))
            expenses = to_money(float(paid) * rng.uniform(0.35, 0.55))
            closed_at = None
        elif status_value in {
            OrderStatus.IN_PROGRESS.value,
            OrderStatus.CONTRACT.value,
        }:
            paid = to_money(float(amount) * 0.5)
            expenses = to_money(float(paid) * rng.uniform(0.3, 0.5))
            closed_at = None
        elif status_value == OrderStatus.APPROVED.value:
            paid = to_money(float(amount) * rng.uniform(0, 0.3))
            expenses = to_money(float(paid) * 0.2)
            closed_at = None
        else:
            paid = to_money(0)
            expenses = to_money(0)
            closed_at = None

        year = created_at.year
        year_counters[year] = year_counters.get(year, 0) + 1
        manager_user = rng.choice(staff)
        source = rng.choice(["dashboard", "dashboard", "telegram"])
        sla_hours = get_sla_hours(practice)
        if status_value in {
            OrderStatus.NEW.value,
            OrderStatus.QUALIFIED.value,
            OrderStatus.PROPOSAL.value,
        }:
            sla_due_at = created_at + timedelta(hours=sla_hours)
        elif status_value in {
            OrderStatus.APPROVED.value,
            OrderStatus.CONTRACT.value,
            OrderStatus.IN_PROGRESS.value,
        }:
            # На поздних этапах SLA считается от текущей загрузки команды.
            sla_due_at = now + timedelta(days=rng.randint(2, 12))
        else:
            sla_due_at = created_at + timedelta(days=30)

        order = Order(
            number=f"CF-{year}-{year_counters[year]:04d}",
            client=rng.choice(clients),
            practice=practice,
            manager=manager_user,
            title=rng.choice(TITLES[practice]),
            description=rng.choice(DESCRIPTIONS),
            status=status_value,
            amount=amount,
            paid_amount=paid,
            expenses=expenses,
            deadline=(created_at + timedelta(days=rng.randint(20, 80))).date(),
            sla_due_at=sla_due_at,
            source=source,
            bot_user_id=bot_client.id if source == "telegram" else None,
            created_at=created_at,
            updated_at=created_at,
            closed_at=closed_at,
        )
        db.add(order)
        db.flush()
        orders.append(order)

        # История статусов: последовательный путь до текущего статуса.
        path = [OrderStatus.NEW.value]
        if status_value == OrderStatus.CANCELLED.value:
            path = [OrderStatus.NEW.value, OrderStatus.CANCELLED.value]
        elif status_value in STATUS_PATH:
            path = STATUS_PATH[: STATUS_PATH.index(status_value) + 1]

        previous = None
        for index, step in enumerate(path):
            event_time = created_at + timedelta(hours=index * rng.randint(6, 30))
            if event_time > now:
                event_time = now
            db.add(
                OrderEvent(
                    order_id=order.id,
                    from_status=previous,
                    to_status=step,
                    comment="Заявка создана" if previous is None else "Статус обновлён",
                    actor_type="system" if previous is None else "user",
                    actor_id=manager_user.id if previous is not None else None,
                    created_at=event_time,
                )
            )
            previous = step

        # Документы, соответствующие пройденным этапам.
        doc_types = [DocumentType.REQUEST.value]
        if status_value in STATUS_PATH and STATUS_PATH.index(status_value) >= STATUS_PATH.index(
            OrderStatus.PROPOSAL.value
        ):
            doc_types.append(DocumentType.PROPOSAL.value)
        if status_value in STATUS_PATH and STATUS_PATH.index(status_value) >= STATUS_PATH.index(
            OrderStatus.CONTRACT.value
        ):
            doc_types.append(DocumentType.CONTRACT.value)
        if status_value in {OrderStatus.DONE.value, OrderStatus.CLOSED.value}:
            doc_types.append(DocumentType.ACT.value)

        for doc_type in doc_types:
            payload = build_document(order, doc_type)
            db.add(
                Document(
                    order_id=order.id,
                    doc_type=doc_type,
                    number=payload["number"],
                    status="signed"
                    if doc_type in {DocumentType.CONTRACT.value, DocumentType.ACT.value}
                    else "draft",
                    payload=payload,
                    created_at=created_at + timedelta(hours=2),
                )
            )

    db.commit()
    return True
