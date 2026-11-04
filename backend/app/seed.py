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
from app.models import (
    BotUser,
    Client,
    Document,
    Order,
    OrderEvent,
    OrderWorkflow,
    User,
)
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
        full_name="Иван Петров",
        phone="+7 (914) 123-45-67",
        email="petrov@vektor.ru",
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

    # Демо-клиент «Вектор» связывается с Telegram-ботом в seed_prototype().

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


def _demo_client(
    db: Session, name: str, contact: str, email: str
) -> Client:
    client = db.scalar(select(Client).where(Client.name == name))
    if client is None:
        client = Client(name=name, contact_person=contact, email=email)
        db.add(client)
        db.flush()
    else:
        client.contact_person = contact
        client.email = email
    return client


def _demo_event(
    db: Session,
    order: Order,
    *,
    to_status: str,
    comment: str,
    created_at,
    from_status: str | None = None,
    actor_type: str = "system",
) -> None:
    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=from_status,
            to_status=to_status,
            comment=comment,
            actor_type=actor_type,
            created_at=created_at,
        )
    )


def _demo_documents(
    db: Session, order: Order, items: list[tuple[str, str, object]]
) -> None:
    for doc_type, status, created_at in items:
        payload = build_document(order, doc_type)
        db.add(
            Document(
                order_id=order.id,
                doc_type=doc_type,
                number=payload["number"],
                status=status,
                payload=payload,
                created_at=created_at,
            )
        )


def seed_prototype(db: Session) -> bool:
    """Добавляет четыре демо-заявки и связывает «Вектор» с Telegram-ботом.

    Функция идемпотентна и вызывается отдельно от seed(), чтобы демо-сценарий
    появился и в уже существующей базе.
    """
    now = utcnow()
    demo = _demo_client(db, "ООО «Вектор»", "Иван Петров", "petrov@vektor.ru")

    bot_user = db.scalar(
        select(BotUser).where(BotUser.telegram_id == 700000001)
    )
    if bot_user is not None:
        bot_user.full_name = "Иван Петров"
        bot_user.email = "petrov@vektor.ru"
        bot_user.username = bot_user.username or "demo_client"

    # У одного клиента может быть только один Telegram-аккаунт.
    for other in db.scalars(
        select(Client).where(
            Client.telegram_id == 700000001, Client.id != demo.id
        )
    ).all():
        other.telegram_id = None
    demo.telegram_id = 700000001

    manager = db.scalar(select(User).where(User.email == "a.ivanov@consultflow.ru"))
    if manager is None:
        manager = User(
            email="a.ivanov@consultflow.ru",
            full_name="Алексей Иванов",
            password_hash=hash_password("manager12345"),
            role=UserRole.MANAGER.value,
        )
        db.add(manager)
    db.commit()

    if db.scalar(select(Order).where(Order.source == "prototype").limit(1)):
        return False

    alfa = _demo_client(db, "ООО «Альфа»", "Мария Соколова", "sokolova@alfa.ru")
    romashka = _demo_client(
        db, "ООО «Ромашка»", "Ольга Кузнецова", "kuznetsova@romashka.ru"
    )
    start = _demo_client(db, "ООО «Старт»", "Павел Орлов", "orlov@start.ru")
    year = now.year

    # 104 — новая заявка, с которой начинается основной сценарий.
    created = now - timedelta(hours=2)
    order_104 = Order(
        number=f"CF-{year}-0104",
        client=demo,
        manager=manager,
        practice=Practice.MANAGEMENT.value,
        title="Разработка стратегии развития на 2026–2028 годы",
        description=(
            "Нужна помощь с разработкой стратегии развития компании: "
            "диагностика, интервью с руководителями и итоговая презентация."
        ),
        status=OrderStatus.NEW.value,
        amount=to_money(45000),
        deadline=(now + timedelta(days=1)).date(),
        sla_due_at=now + timedelta(days=1),
        source="prototype",
        created_at=created,
        updated_at=created + timedelta(hours=2),
    )
    db.add(order_104)
    db.flush()
    db.add(
        OrderWorkflow(
            order_id=order_104.id,
            display_number="104",
            file_name="Бриф_Вектор.pdf",
            consultant_name="Анна Смирнова",
            solution=(
                "Провести диагностику, интервью с руководителями и подготовить "
                "стратегию развития на 2026–2028 годы."
            ),
            duration_days=5,
            sla_text="Ответ на обращение в течение 1 рабочего дня",
            practice_confirmed=True,
            created_at=created,
            updated_at=created + timedelta(hours=2),
        )
    )
    _demo_event(
        db, order_104, to_status=OrderStatus.NEW.value,
        comment="Заявка зарегистрирована", created_at=created,
    )
    _demo_event(
        db, order_104, to_status=OrderStatus.NEW.value,
        comment="Данные извлечены, дубликаты не найдены",
        created_at=created + timedelta(hours=1), from_status=OrderStatus.NEW.value,
    )
    _demo_event(
        db, order_104, to_status=OrderStatus.NEW.value,
        comment="Практика и консультант подтверждены",
        created_at=created + timedelta(hours=2), from_status=OrderStatus.NEW.value,
    )
    _demo_documents(
        db, order_104,
        [(DocumentType.REQUEST.value, "draft", created + timedelta(minutes=20))],
    )

    # 103 — заявка на уточнении.
    created = now - timedelta(days=1, hours=3)
    order_103 = Order(
        number=f"CF-{year}-0103",
        client=alfa,
        manager=manager,
        practice=Practice.FINANCE.value,
        title="Постановка управленческого учёта",
        description="Требуется поставить управленческий учёт и обучить команду.",
        status=OrderStatus.CLARIFICATION.value,
        amount=to_money(0),
        deadline=(now + timedelta(days=2)).date(),
        sla_due_at=now + timedelta(days=2),
        source="prototype",
        created_at=created,
        updated_at=created + timedelta(days=1),
    )
    db.add(order_103)
    db.flush()
    db.add(
        OrderWorkflow(
            order_id=order_103.id,
            display_number="103",
            file_name="ТЗ_Альфа.pdf",
            consultant_name="Дмитрий Орлов",
            duration_days=7,
            sla_text="Ответ на обращение в течение 1 рабочего дня",
            clarification_question=(
                "Уточните, пожалуйста, сколько сотрудников и подразделений "
                "нужно охватить управленческим учётом?"
            ),
            practice_confirmed=True,
            created_at=created,
            updated_at=created + timedelta(days=1),
        )
    )
    _demo_event(
        db, order_103, to_status=OrderStatus.NEW.value,
        comment="Заявка зарегистрирована", created_at=created,
    )
    _demo_event(
        db, order_103, to_status=OrderStatus.NEW.value,
        comment="Данные извлечены, дубликаты не найдены",
        created_at=created + timedelta(hours=1), from_status=OrderStatus.NEW.value,
    )
    _demo_event(
        db, order_103, to_status=OrderStatus.NEW.value,
        comment="Практика и консультант подтверждены",
        created_at=created + timedelta(hours=2), from_status=OrderStatus.NEW.value,
    )
    _demo_event(
        db, order_103, to_status=OrderStatus.CLARIFICATION.value,
        comment="Уточнение отправлено клиенту",
        created_at=created + timedelta(days=1),
        from_status=OrderStatus.NEW.value,
    )
    _demo_documents(
        db, order_103,
        [(DocumentType.REQUEST.value, "draft", created + timedelta(minutes=20))],
    )

    # 102 — КП подписано, договор сформирован, работа идёт.
    created = now - timedelta(days=8)
    order_102 = Order(
        number=f"CF-{year}-0102",
        client=romashka,
        manager=manager,
        practice=Practice.LEGAL.value,
        title="Правовая экспертиза договорного портфеля",
        description="Проверить договоры поставки и подготовить рекомендации.",
        status=OrderStatus.IN_PROGRESS.value,
        amount=to_money(120000),
        paid_amount=to_money(60000),
        expenses=to_money(20000),
        deadline=(now + timedelta(days=8)).date(),
        sla_due_at=now + timedelta(days=8),
        source="prototype",
        created_at=created,
        updated_at=now - timedelta(days=2),
    )
    db.add(order_102)
    db.flush()
    db.add(
        OrderWorkflow(
            order_id=order_102.id,
            display_number="102",
            file_name="Договоры_Ромашка.zip",
            consultant_name="Мария Ковалёва",
            solution=(
                "Провести правовую экспертизу договорного портфеля, "
                "подготовить карту рисков и рекомендации по правкам."
            ),
            duration_days=10,
            sla_text="Ответ на обращение в течение 1 рабочего дня",
            proposal_version=1,
            practice_confirmed=True,
            signed_at=now - timedelta(days=5),
            contract_at=now - timedelta(days=4),
            work_started_at=now - timedelta(days=2),
            created_at=created,
            updated_at=now - timedelta(days=2),
        )
    )
    for index, (status, comment) in enumerate(
        [
            (OrderStatus.NEW.value, "Заявка зарегистрирована"),
            (OrderStatus.QUALIFIED.value, "Заявка квалифицирована"),
            (OrderStatus.PROPOSAL.value, "КП отправлено"),
            (OrderStatus.APPROVED.value, "КП подписано и сохранено"),
            (OrderStatus.CONTRACT.value, "Договор сформирован"),
            (OrderStatus.IN_PROGRESS.value, "Работа начата"),
        ]
    ):
        _demo_event(
            db, order_102,
            to_status=status,
            comment=comment,
            created_at=created + timedelta(days=index),
            from_status=None if index == 0 else [
                OrderStatus.NEW.value,
                OrderStatus.QUALIFIED.value,
                OrderStatus.PROPOSAL.value,
                OrderStatus.APPROVED.value,
                OrderStatus.CONTRACT.value,
            ][index - 1],
        )
    _demo_documents(
        db, order_102,
        [
            (DocumentType.REQUEST.value, "draft", created + timedelta(minutes=20)),
            (DocumentType.PROPOSAL.value, "signed", created + timedelta(days=1)),
            (DocumentType.CONTRACT.value, "signed", created + timedelta(days=3)),
        ],
    )

    # 101 — завершённая заявка с подписанным актом.
    created = now - timedelta(days=20)
    order_101 = Order(
        number=f"CF-{year}-0101",
        client=start,
        manager=manager,
        practice=Practice.IT.value,
        title="Внедрение BI-отчётности для руководства",
        description="Собрать требования и внедрить управленческую BI-отчётность.",
        status=OrderStatus.DONE.value,
        amount=to_money(78000),
        paid_amount=to_money(78000),
        expenses=to_money(30000),
        deadline=(now - timedelta(days=2)).date(),
        sla_due_at=now - timedelta(days=2),
        source="prototype",
        created_at=created,
        updated_at=now - timedelta(days=1),
    )
    db.add(order_101)
    db.flush()
    db.add(
        OrderWorkflow(
            order_id=order_101.id,
            display_number="101",
            file_name="ТЗ_Старт.pdf",
            consultant_name="Анна Смирнова",
            solution=(
                "Собрать требования, настроить BI-дашборды и обучить "
                "руководителей работе с отчётностью."
            ),
            duration_days=7,
            sla_text="Ответ на обращение в течение 1 рабочего дня",
            proposal_version=1,
            practice_confirmed=True,
            signed_at=now - timedelta(days=16),
            contract_at=now - timedelta(days=14),
            work_started_at=now - timedelta(days=12),
            act_at=now - timedelta(days=2),
            act_confirmed_at=now - timedelta(days=1),
            created_at=created,
            updated_at=now - timedelta(days=1),
        )
    )
    for index, (status, comment) in enumerate(
        [
            (OrderStatus.NEW.value, "Заявка зарегистрирована"),
            (OrderStatus.QUALIFIED.value, "Заявка квалифицирована"),
            (OrderStatus.PROPOSAL.value, "КП отправлено"),
            (OrderStatus.APPROVED.value, "КП подписано и сохранено"),
            (OrderStatus.CONTRACT.value, "Договор сформирован"),
            (OrderStatus.IN_PROGRESS.value, "Работа начата"),
            (OrderStatus.DONE.value, "Акт подтверждён, заказ завершён"),
        ]
    ):
        _demo_event(
            db, order_101,
            to_status=status,
            comment=comment,
            created_at=created + timedelta(days=index * 2),
            from_status=None if index == 0 else [
                OrderStatus.NEW.value,
                OrderStatus.QUALIFIED.value,
                OrderStatus.PROPOSAL.value,
                OrderStatus.APPROVED.value,
                OrderStatus.CONTRACT.value,
                OrderStatus.IN_PROGRESS.value,
            ][index - 1],
        )
    _demo_documents(
        db, order_101,
        [
            (DocumentType.REQUEST.value, "draft", created + timedelta(minutes=20)),
            (DocumentType.PROPOSAL.value, "signed", created + timedelta(days=2)),
            (DocumentType.CONTRACT.value, "signed", created + timedelta(days=6)),
            (DocumentType.ACT.value, "signed", created + timedelta(days=18)),
        ],
    )

    db.commit()
    return True
