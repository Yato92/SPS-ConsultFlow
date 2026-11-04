"""Состояния FSM для оформления заявки."""

from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    practice = State()
    title = State()
    description = State()
    hours = State()
    complexity = State()
    client_name = State()
    phone = State()
    confirm = State()
