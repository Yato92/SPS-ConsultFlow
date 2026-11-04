"""Справочники и перечисления предметной области ConsultFlow."""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CONSULTANT = "consultant"
    LAWYER = "lawyer"
    FINANCE = "finance"


class BotRole(str, Enum):
    CLIENT = "client"
    MANAGER = "manager"


class OrderStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    APPROVED = "approved"
    CONTRACT = "contract"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Practice(str, Enum):
    MANAGEMENT = "management"
    FINANCE = "finance"
    LEGAL = "legal"
    IT = "it"


class ActorType(str, Enum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class DocumentType(str, Enum):
    REQUEST = "request"
    PROPOSAL = "proposal"
    CONTRACT = "contract"
    ACT = "act"


USER_ROLE_LABELS: dict[str, str] = {
    UserRole.ADMIN.value: "Администратор",
    UserRole.MANAGER.value: "Менеджер",
    UserRole.CONSULTANT.value: "Консультант",
    UserRole.LAWYER.value: "Юрист",
    UserRole.FINANCE.value: "Финансист",
}

STATUS_LABELS: dict[str, str] = {
    OrderStatus.NEW.value: "Новая заявка",
    OrderStatus.QUALIFIED.value: "Квалифицирована",
    OrderStatus.PROPOSAL.value: "КП отправлено",
    OrderStatus.APPROVED.value: "КП согласовано",
    OrderStatus.CONTRACT.value: "Договор подписан",
    OrderStatus.IN_PROGRESS.value: "В работе",
    OrderStatus.DONE.value: "Работы выполнены",
    OrderStatus.CLOSED.value: "Закрыт",
    OrderStatus.CANCELLED.value: "Отменён",
}

STATUS_COLORS: dict[str, str] = {
    OrderStatus.NEW.value: "blue",
    OrderStatus.QUALIFIED.value: "geekblue",
    OrderStatus.PROPOSAL.value: "gold",
    OrderStatus.APPROVED.value: "lime",
    OrderStatus.CONTRACT.value: "cyan",
    OrderStatus.IN_PROGRESS.value: "purple",
    OrderStatus.DONE.value: "green",
    OrderStatus.CLOSED.value: "default",
    OrderStatus.CANCELLED.value: "red",
}

PRACTICE_LABELS: dict[str, str] = {
    Practice.MANAGEMENT.value: "Управленческий консалтинг",
    Practice.FINANCE.value: "Финансовый консалтинг",
    Practice.LEGAL.value: "Юридический консалтинг",
    Practice.IT.value: "IT-консалтинг",
}

DOCUMENT_LABELS: dict[str, str] = {
    DocumentType.REQUEST.value: "Заявка",
    DocumentType.PROPOSAL.value: "Коммерческое предложение",
    DocumentType.CONTRACT.value: "Договор",
    DocumentType.ACT.value: "Акт выполненных работ",
}

# Разрешённые переходы статусов (жизненный цикл заказа).
STATUS_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.NEW.value: {
        OrderStatus.QUALIFIED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.QUALIFIED.value: {
        OrderStatus.PROPOSAL.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.PROPOSAL.value: {
        OrderStatus.APPROVED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.APPROVED.value: {
        OrderStatus.CONTRACT.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.CONTRACT.value: {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.IN_PROGRESS.value: {
        OrderStatus.DONE.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.DONE.value: {OrderStatus.CLOSED.value},
    OrderStatus.CLOSED.value: set(),
    OrderStatus.CANCELLED.value: set(),
}

ACTIVE_STATUSES = {
    OrderStatus.NEW.value,
    OrderStatus.QUALIFIED.value,
    OrderStatus.PROPOSAL.value,
    OrderStatus.APPROVED.value,
    OrderStatus.CONTRACT.value,
    OrderStatus.IN_PROGRESS.value,
}
