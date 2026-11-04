"""Справочник сотрудников (для выбора менеджера и ролей)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    role: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[UserOut]:
    query = select(User).where(User.is_active.is_(True))
    if role:
        query = query.where(User.role == role)
    users = db.scalars(query.order_by(User.full_name)).all()
    return [UserOut.model_validate(user) for user in users]
