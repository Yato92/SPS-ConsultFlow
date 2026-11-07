"""Точка входа FastAPI-приложения ConsultFlow."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes import (
    analytics,
    auth,
    bot,
    client,
    clients,
    orders,
    prototype,
    telegram,
    users,
)
from app.core.config import get_settings
from app.core.enums import PRACTICE_LABELS, STATUS_LABELS
from app.db.session import Base, SessionLocal, engine
from app.seed import seed, seed_prototype

settings = get_settings()


def ensure_soft_delete_columns() -> None:
    """Добавляет поля мягкого удаления в существующую таблицу orders.

    `create_all` не меняет уже созданные таблицы, поэтому для работающей базы
    (SQLite локально, PostgreSQL на сервере) выполняем безопасный ALTER TABLE.
    """
    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("orders")}
    is_sqlite = engine.dialect.name == "sqlite"
    timestamp_type = "DATETIME" if is_sqlite else "TIMESTAMP"
    statements: list[str] = []
    if "is_deleted" not in columns:
        default = "0" if is_sqlite else "FALSE"
        statements.append(
            f"ALTER TABLE orders ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT {default}"
        )
    if "deleted_at" not in columns:
        statements.append(f"ALTER TABLE orders ADD COLUMN deleted_at {timestamp_type} NULL")
    if "deleted_by" not in columns:
        statements.append("ALTER TABLE orders ADD COLUMN deleted_by INTEGER NULL")
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_orders_is_deleted "
                    "ON orders (is_deleted)"
                )
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_soft_delete_columns()
    if settings.seed_demo:
        with SessionLocal() as db:
            seed(db)
            seed_prototype(db)
    yield


app = FastAPI(
    title="ConsultFlow API",
    description=(
        "Бэкенд цифрового продукта ConsultFlow: заявки, заказы, документы, "
        "аналитика и интеграция с Telegram-ботом."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(auth.router, prefix=api)
app.include_router(analytics.router, prefix=api)
app.include_router(orders.router, prefix=api)
app.include_router(clients.router, prefix=api)
app.include_router(client.router, prefix=api)
app.include_router(users.router, prefix=api)
app.include_router(telegram.router, prefix=api)
app.include_router(bot.router, prefix=api)
app.include_router(prototype.router, prefix=api)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "ConsultFlow API", "version": "1.0.0"}


@app.get("/health/db", tags=["system"])
def health_db() -> dict:
    """Проверка подключения к внешней БД (reg.ru, PostgreSQL, MySQL)."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail="База данных недоступна. Проверьте DATABASE_URL и сетевой доступ.",
        ) from exc
    return {"status": "ok", "dialect": engine.dialect.name}


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "name": "ConsultFlow API",
        "slogan": "От заявки до акта — один процесс",
        "docs": "/api/docs",
        "health": "/health",
        "statuses": STATUS_LABELS,
        "practices": PRACTICE_LABELS,
    }
