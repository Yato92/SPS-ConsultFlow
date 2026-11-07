"""Публичный API учебного прототипа ConsultFlow.

Эндпоинты используются статическим прототипом в ``frontend/public/prototype``.
Доступ включается флагом ``PROTOTYPE_DEMO``; в учебном стенде он включён.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas import (
    PrototypeAnswerIn,
    PrototypeBootstrapOut,
    PrototypeClarifyIn,
    PrototypeOrderCreate,
    PrototypeOrderOut,
    PrototypePaymentIn,
    PrototypePracticeIn,
    PrototypeProposalIn,
    PrototypeRemarksIn,
)
from app.services import prototype as service

router = APIRouter(prefix="/prototype", tags=["prototype"])


def require_demo_enabled() -> None:
    if not get_settings().prototype_demo:
        raise HTTPException(status_code=404, detail="Прототип отключён")


router.dependencies.append(Depends(require_demo_enabled))


def _error(exc: service.PrototypeError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/bootstrap", response_model=PrototypeBootstrapOut)
def bootstrap(
    order_id: int | None = Query(default=None, ge=1),
    include_external: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> PrototypeBootstrapOut:
    return service.bootstrap(db, order_id, include_external=include_external)


@router.get("/orders", response_model=list[PrototypeOrderOut])
def list_orders(
    include_external: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[PrototypeOrderOut]:
    return [
        service.serialize_order(db, order)
        for order in service.demo_orders(db, include_external=include_external)
    ]


@router.get("/orders/{order_id}", response_model=PrototypeOrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
    except service.PrototypeError as exc:
        raise _error(exc) from exc
    return service.serialize_order(db, order)


@router.post("/orders", response_model=PrototypeOrderOut, status_code=201)
def create_order(
    payload: PrototypeOrderCreate, db: Session = Depends(get_db)
) -> PrototypeOrderOut:
    return service.create_prototype_order(db, payload)


@router.post("/orders/{order_id}/clarify", response_model=PrototypeOrderOut)
def clarify(
    order_id: int,
    payload: PrototypeClarifyIn,
    db: Session = Depends(get_db),
) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.request_clarification(db, order, payload)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/answer", response_model=PrototypeOrderOut)
def answer(
    order_id: int,
    payload: PrototypeAnswerIn,
    db: Session = Depends(get_db),
) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.submit_answer(db, order, payload)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/proposal", response_model=PrototypeOrderOut)
def proposal(
    order_id: int,
    payload: PrototypeProposalIn,
    db: Session = Depends(get_db),
) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.send_proposal(db, order, payload)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/sign", response_model=PrototypeOrderOut)
def sign(order_id: int, db: Session = Depends(get_db)) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.sign_proposal(db, order)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/remarks", response_model=PrototypeOrderOut)
def remarks(
    order_id: int,
    payload: PrototypeRemarksIn,
    db: Session = Depends(get_db),
) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.submit_remarks(db, order, payload)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/contract", response_model=PrototypeOrderOut)
def contract(order_id: int, db: Session = Depends(get_db)) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.form_contract(db, order)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/start", response_model=PrototypeOrderOut)
def start(order_id: int, db: Session = Depends(get_db)) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.start_work(db, order)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/act", response_model=PrototypeOrderOut)
def act(order_id: int, db: Session = Depends(get_db)) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.form_act(db, order)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/confirm-act", response_model=PrototypeOrderOut)
def confirm_act(order_id: int, db: Session = Depends(get_db)) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.confirm_act(db, order)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/practice", response_model=PrototypeOrderOut)
def practice(
    order_id: int,
    payload: PrototypePracticeIn,
    db: Session = Depends(get_db),
) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.update_practice(db, order, payload)
    except service.PrototypeError as exc:
        raise _error(exc) from exc


@router.post("/orders/{order_id}/pay", response_model=PrototypeOrderOut)
def pay(
    order_id: int,
    payload: PrototypePaymentIn,
    db: Session = Depends(get_db),
) -> PrototypeOrderOut:
    try:
        order = service.get_order(db, order_id)
        return service.pay_order(db, order, payload)
    except service.PrototypeError as exc:
        raise _error(exc) from exc
