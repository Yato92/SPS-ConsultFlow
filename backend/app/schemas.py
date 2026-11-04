"""Pydantic-схемы API ConsultFlow."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import DocumentType, OrderStatus, Practice, UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Пользователи и авторизация ----------


class UserBrief(ORMModel):
    id: int
    full_name: str
    role: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    telegram_id: int | None = None
    is_active: bool


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class MagicIn(BaseModel):
    token: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Клиенты ----------


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    inn: str | None = Field(default=None, max_length=12)
    contact_person: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    telegram_id: int | None = None


class ClientOut(ORMModel):
    id: int
    name: str
    inn: str | None = None
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram_id: int | None = None
    created_at: datetime


class ClientStatsOut(ClientOut):
    orders_count: int = 0
    paid_total: float = 0
    profit: float = 0


class ClientListOut(BaseModel):
    items: list[ClientStatsOut]
    total: int


# ---------- Заказы ----------


class OrderEventOut(ORMModel):
    id: int
    from_status: str | None = None
    to_status: str
    comment: str | None = None
    actor_type: str
    actor_id: int | None = None
    created_at: datetime


class DocumentOut(ORMModel):
    id: int
    doc_type: str
    number: str
    status: str
    payload: dict[str, Any]
    created_at: datetime


class DocumentCreate(BaseModel):
    doc_type: DocumentType


class OrderOut(ORMModel):
    id: int
    number: str
    title: str
    description: str | None = None
    practice: str
    status: str
    amount: float
    paid_amount: float
    expenses: float
    deadline: date | None = None
    sla_due_at: datetime | None = None
    source: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    is_overdue: bool = False
    client: ClientOut
    manager: UserBrief | None = None


class OrderDetailOut(OrderOut):
    events: list[OrderEventOut] = []
    documents: list[DocumentOut] = []


class OrderListOut(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    page_size: int
    pages: int


class OrderCreate(BaseModel):
    client_id: int
    practice: Practice
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    manager_id: int | None = None
    amount: float = Field(default=0, ge=0)
    deadline: date | None = None


class OrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    practice: Practice | None = None
    manager_id: int | None = None
    amount: float | None = Field(default=None, ge=0)
    paid_amount: float | None = Field(default=None, ge=0)
    expenses: float | None = Field(default=None, ge=0)
    deadline: date | None = None


class StatusChangeIn(BaseModel):
    status: OrderStatus
    comment: str | None = Field(default=None, max_length=500)


# ---------- Дашборд ----------


class SummaryOut(BaseModel):
    orders_total: int
    active_orders: int
    closed_orders: int
    amount_total: float
    paid_total: float
    expenses_total: float
    profit: float
    avg_check: float
    conversion: float
    overdue_count: int
    avg_cycle_days: float


class MonthlyPoint(BaseModel):
    month: str
    label: str
    orders: int
    paid: float
    expenses: float
    profit: float


class PracticeStat(BaseModel):
    practice: str
    label: str
    orders: int
    amount: float
    paid: float
    expenses: float
    profit: float


class StatusStat(BaseModel):
    status: str
    label: str
    count: int
    amount: float


class ManagerStat(BaseModel):
    manager_id: int | None
    name: str
    orders: int
    paid: float
    profit: float


class DashboardOut(BaseModel):
    summary: SummaryOut
    monthly: list[MonthlyPoint]
    by_practice: list[PracticeStat]
    by_status: list[StatusStat]
    managers: list[ManagerStat]
    recent_orders: list[OrderOut]
    overdue_orders: list[OrderOut]
    generated_at: datetime


# ---------- Telegram-бот ----------


class BotUserIn(BaseModel):
    telegram_id: int
    username: str | None = None
    full_name: str = ""
    phone: str | None = None
    email: str | None = None


class BotUserOut(ORMModel):
    id: int
    telegram_id: int
    username: str | None = None
    full_name: str
    role: str
    user_id: int | None = None


class BotRegisterOut(BaseModel):
    user: BotUserOut
    is_manager: bool
    manager_name: str | None = None


class BotUserRow(BotUserOut):
    created_at: datetime
    orders_count: int = 0


class BotEstimateOut(BaseModel):
    rate: float
    hours: float
    multiplier: float
    amount: float
    sla_hours: int


class BotOrderIn(BaseModel):
    telegram_id: int
    practice: Practice
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    hours: float = Field(default=8, gt=0, le=2000)
    complexity: str = Field(default="standard", pattern="^(basic|standard|complex)$")
    client_name: str | None = None
    phone: str | None = None
    email: str | None = None


class BotOrderOut(BaseModel):
    id: int
    number: str
    title: str
    status: str
    status_label: str
    practice: str
    practice_label: str
    amount: float
    created_at: datetime
    sla_due_at: datetime | None = None
    estimate: BotEstimateOut


class BotOrderShort(BaseModel):
    id: int
    number: str
    title: str
    status: str
    status_label: str
    amount: float
    created_at: datetime


class BotOrderDetailOut(BotOrderShort):
    practice: str
    practice_label: str
    client_name: str | None = None
    description: str | None = None
    sla_due_at: datetime | None = None
    is_overdue: bool = False
    events: list[OrderEventOut] = []


class BotStatusIn(BaseModel):
    telegram_id: int
    status: OrderStatus
    comment: str | None = None


class BotLinkOut(BaseModel):
    url: str
    expires_in_minutes: int


class BotStatsOut(BaseModel):
    orders_total: int
    active_orders: int
    paid_total: float
    profit: float
    overdue_count: int
    conversion: float
    new_orders: int
    generated_at: datetime


class NotificationOut(ORMModel):
    id: int
    order_id: int | None = None
    recipient: str
    text: str
    created_at: datetime


class NotificationAckIn(BaseModel):
    ids: list[int]


class PricingInfoOut(BaseModel):
    practices: list[dict[str, Any]]
    complexities: list[dict[str, Any]]
