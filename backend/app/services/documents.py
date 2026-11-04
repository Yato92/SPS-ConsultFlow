"""Автоматическая подготовка документов по заказу."""

from datetime import datetime

from app.core.enums import (
    PRACTICE_LABELS,
    DocumentType,
    OrderStatus,
    STATUS_LABELS,
)
from app.core.utils import format_money, utcnow
from app.models import Order

DOC_PREFIX = {
    DocumentType.REQUEST.value: "ЗАЯВКА",
    DocumentType.PROPOSAL.value: "КП",
    DocumentType.CONTRACT.value: "ДОГОВОР",
    DocumentType.ACT.value: "АКТ",
    DocumentType.PAYMENT.value: "ЧЕК",
}


def document_number(order: Order, doc_type: str) -> str:
    prefix = DOC_PREFIX.get(doc_type, "ДОК")
    year = (order.created_at or utcnow()).year
    return f"{prefix}-{year}-{order.id:04d}"


def _deadline(order: Order) -> str:
    if order.deadline:
        return order.deadline.strftime("%d.%m.%Y")
    return "согласовывается сторонами"


def _manager(order: Order) -> str:
    return order.manager.full_name if order.manager else "менеджер ConsultFlow"


def build_document(order: Order, doc_type: str) -> dict:
    """Формирует черновик документа (markdown-текст + метаданные)."""
    client_name = order.client.name if order.client else "Клиент"
    practice = PRACTICE_LABELS.get(order.practice, order.practice)
    amount = format_money(order.amount)
    number = document_number(order, doc_type)
    created = datetime.now().strftime("%d.%m.%Y")

    common = {
        "order_number": order.number,
        "client": client_name,
        "practice": practice,
        "amount": amount,
        "manager": _manager(order),
        "created": created,
    }

    if doc_type == DocumentType.REQUEST.value:
        title = f"Заявка на консалтинговые услуги № {number}"
        body = f"""# {title}

**Дата:** {created}
**Клиент:** {client_name}
**Направление:** {practice}
**Менеджер:** {_manager(order)}

## Предмет заявки
{order.title}

{order.description or "Описание уточняется на этапе квалификации."}

## Ожидаемый результат
Подготовка рекомендаций и итогового отчёта по проекту.

## Срок
{_deadline(order)}
"""
    elif doc_type == DocumentType.PROPOSAL.value:
        title = f"Коммерческое предложение № {number}"
        body = f"""# {title}

**Клиент:** {client_name}
**Дата подготовки:** {created}
**Направление:** {practice}

## 1. Задача клиента
{order.title}

## 2. Состав работ
1. Диагностика текущей ситуации и сбор исходных данных.
2. Разработка рекомендаций по направлению «{practice}».
3. Подготовка итогового отчёта и презентация результатов.

## 3. Стоимость и сроки
| Показатель | Значение |
| --- | --- |
| Стоимость работ | {amount} |
| Срок выполнения | {_deadline(order)} |
| Менеджер проекта | {_manager(order)} |

## 4. Условия
Оплата производится в два этапа: 50 % — аванс, 50 % — после подписания акта.
Предложение действительно 14 календарных дней.
"""
    elif doc_type == DocumentType.PAYMENT.value:
        paid = format_money(order.paid_amount or order.amount)
        title = f"Чек об оплате № {number}"
        body = f"""# {title}

**Заказчик:** {client_name}
**Заказ:** {order.number} — {order.title}
**Дата:** {created}

## Платёж
| Показатель | Значение |
| --- | --- |
| Сумма | {paid} |
| Способ | Банковская карта |
| Режим | Тестовый платёж, деньги не списываются |

Оплата принята. Чек сформирован автоматически в учебном контуре ConsultFlow.
"""
    elif doc_type == DocumentType.CONTRACT.value:
        title = f"Договор возмездного оказания услуг № {number}"
        body = f"""# {title}

**Заказчик:** {client_name}
**Исполнитель:** ООО «ConsultFlow»
**Дата:** {created}

## 1. Предмет договора
Исполнитель оказывает заказчику консалтинговые услуги по направлению
«{practice}» в рамках заказа {order.number}: {order.title}.

## 2. Стоимость работ
Стоимость услуг составляет {amount}.

## 3. Сроки
Работы выполняются до {_deadline(order)}.

## 4. Порядок сдачи-приёмки
По завершении работ исполнитель направляет заказчику акт выполненных работ.
Заказчик подписывает акт в течение 5 рабочих дней либо направляет мотивированные
замечания.

## 5. Ответственные лица
Менеджер проекта со стороны исполнителя — {_manager(order)}.
"""
    else:
        title = f"Акт выполненных работ № {number}"
        body = f"""# {title}

**Заказчик:** {client_name}
**Исполнитель:** ООО «ConsultFlow»
**Дата:** {created}

По договору в рамках заказа {order.number} исполнитель выполнил следующие работы
по направлению «{practice}»:

1. Диагностика и сбор исходных данных.
2. Разработка рекомендаций.
3. Подготовка итогового отчёта и презентация результатов.

**Стоимость выполненных работ:** {amount}
**Статус заказа:** {STATUS_LABELS.get(order.status, order.status)}

Работы выполнены в полном объёме, замечаний нет.

Менеджер проекта: {_manager(order)}
"""

    return {
        "title": title,
        "number": number,
        "doc_type": doc_type,
        "body": body,
        "meta": common,
    }


def document_for_status(order: Order, status: str) -> str | None:
    """Определяет, какой документ создаётся при переходе в статус."""
    mapping = {
        OrderStatus.PROPOSAL.value: DocumentType.PROPOSAL.value,
        OrderStatus.CONTRACT.value: DocumentType.CONTRACT.value,
        OrderStatus.DONE.value: DocumentType.ACT.value,
    }
    return mapping.get(status)
