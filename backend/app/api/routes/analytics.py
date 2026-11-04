"""Аналитика для дашборда."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import DashboardOut
from app.services.analytics import build_dashboard
from app.services.pricing import pricing_info

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(
    date_from: date | None = None,
    date_to: date | None = None,
    practice: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardOut:
    return build_dashboard(db, date_from=date_from, date_to=date_to, practice=practice)


@router.get("/pricing")
def pricing(_: User = Depends(get_current_user)) -> dict:
    return pricing_info()
