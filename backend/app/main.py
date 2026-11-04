"""Точка входа FastAPI-приложения ConsultFlow."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    analytics,
    auth,
    bot,
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
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
app.include_router(users.router, prefix=api)
app.include_router(telegram.router, prefix=api)
app.include_router(bot.router, prefix=api)
app.include_router(prototype.router, prefix=api)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "ConsultFlow API", "version": "1.0.0"}


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
