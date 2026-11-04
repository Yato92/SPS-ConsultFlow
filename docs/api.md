# REST API ConsultFlow

Базовый URL: `http://127.0.0.1:8000/api`
Интерактивная документация: `http://127.0.0.1:8000/docs` (Swagger UI), `/redoc`.

## Авторизация

| Сценарий | Заголовок |
| --- | --- |
| Сотрудник в дашборде | `Authorization: Bearer <access_token>` |
| Telegram-бот | `X-Bot-Token: <BOT_API_TOKEN>` |

Access-токен — JWT (HS256), срок 12 часов. Magic-link — JWT типа `magic`, срок 15 минут.
Токен доступа нельзя использовать вместо magic-токена и наоборот.

## Формат ошибок

```json
{ "detail": "Недопустимый переход статуса: new → done" }
```

| Код | Причина |
| --- | --- |
| `401` | нет токена, истёк или неверный тип |
| `403` | роль не позволяет операцию |
| `404` | объект не найден |
| `400` | конфликт бизнес-правила (недопустимый переход статуса) |
| `422` | ошибка валидации тела/параметров |

## Служебные проверки

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/health` | процесс API жив |
| `GET` | `/health/db` | подключение к БД; `dialect` = `sqlite`, `postgresql` или `mysql` |

`/health/db` возвращает `503`, если внешняя база недоступна. Пароль и
`DATABASE_URL` в ответ не попадают.

---

## Аутентификация

### `POST /auth/login`

```json
{ "email": "admin@consultflow.ru", "password": "admin12345" }
```

Ответ:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@consultflow.ru",
    "full_name": "Администратор системы",
    "role": "admin",
    "is_active": true
  }
}
```

### `POST /auth/magic`

```json
{ "token": "<magic-jwt>" }
```

Возвращает `TokenOut` — тот же формат, что и `/auth/login`.

### `GET /auth/me`

Требует Bearer. Возвращает текущего пользователя.

---

## Заказы

### `GET /orders`

| Параметр | Тип | Описание |
| --- | --- | --- |
| `q` | string | поиск по номеру, теме, клиенту |
| `status` | string | один или несколько через запятую |
| `practice` | string | `management`, `finance`, `legal`, `it` |
| `manager_id` | int | фильтр по менеджеру |
| `date_from`, `date_to` | date | период создания (`YYYY-MM-DD`) |
| `page`, `page_size` | int | пагинация (по умолчанию 1 и 20) |
| `sort_by`, `sort_dir` | string | `created_at`, `amount`, `sla_due_at`; `asc`/`desc` |

```json
{
  "items": [
    {
      "id": 42,
      "number": "CF-2026-0042",
      "title": "Аудит ИТ-инфраструктуры",
      "status": "proposal",
      "practice": "it",
      "amount": 240000.0,
      "paid_amount": 120000.0,
      "expenses": 90000.0,
      "is_overdue": false,
      "sla_due_at": "2026-03-05T09:00:00",
      "client": { "id": 7, "name": "ООО «Цифровые решения»" },
      "manager": { "id": 2, "full_name": "Менеджер Проектов" }
    }
  ],
  "total": 72,
  "page": 1,
  "page_size": 20
}
```

### `GET /orders/{id}`

Возвращает `OrderDetailOut`: поля заказа плюс `description`, `hours`, `complexity`,
`source`, `deadline`, `events[]`, `documents[]`.

### `POST /orders`

Роли: `admin`, `manager`.

```json
{
  "client_id": 7,
  "practice": "it",
  "title": "Проектирование интеграционной платформы",
  "description": "Нужна интеграция CRM и 1С",
  "manager_id": 2,
  "amount": 320000,
  "deadline": "2026-05-20"
}
```

Ответ `201` + `OrderOut`. Номер присваивается автоматически.

### `PATCH /orders/{id}`

Роли: `admin`, `manager`. Любое подмножество полей:

```json
{ "amount": 350000, "paid_amount": 175000, "expenses": 120000, "manager_id": 3 }
```

### `POST /orders/{id}/status`

```json
{ "status": "contract", "comment": "Договор подписан клиентом" }
```

Ответ — `OrderDetailOut`. `409`, если переход запрещён словарём статусов.
Администратор может установить любой статус (force).

### `POST /orders/{id}/documents`

```json
{ "doc_type": "proposal" }
```

`doc_type`: `request`, `proposal`, `contract`, `act`. Возвращает `DocumentOut`
с `payload.title`, `payload.body`, `payload.meta`.

### `POST /orders/{id}/documents/{document_id}/sign`

Меняет статус документа на `signed`, фиксирует событие аудита.

### `GET /orders/export/csv`

Экспорт текущей выборки (те же фильтры, что у списка) в CSV с BOM и `;`-разделителем.
Заголовок ответа: `text/csv; charset=utf-8`.

---

## Клиенты

### `GET /clients`

Параметры: `q`, `page`, `page_size`. Возвращает `ClientListOut` c полями
`orders_count`, `paid_total`, `profit`.

### `POST /clients`

Роли: `admin`, `manager`.

```json
{
  "name": "ООО «Новый клиент»",
  "inn": "2700000000",
  "contact_person": "Иванов Иван",
  "email": "client@example.ru",
  "phone": "+7 (4212) 00-00-00"
}
```

### `GET /clients/{id}`

Карточка клиента.

---

## Аналитика

### `GET /dashboard`

Параметры: `date_from`, `date_to`, `practice`, `manager_id`.

```json
{
  "generated_at": "2026-03-01T10:00:00",
  "summary": {
    "orders_total": 72,
    "active_orders": 18,
    "closed_orders": 51,
    "paid_total": 11540000.0,
    "expenses_total": 5110000.0,
    "profit": 6430000.0,
    "avg_check": 160277.0,
    "conversion": 0.71,
    "overdue_count": 2
  },
  "monthly": [{ "label": "апр", "paid": 820000, "expenses": 400000, "profit": 420000 }],
  "by_practice": [
    { "practice": "it", "label": "IT-консалтинг", "orders": 20, "paid": 3200000, "profit": 1800000 }
  ],
  "by_status": [{ "status": "new", "label": "Новая заявка", "count": 6, "amount": 900000 }],
  "managers": [{ "manager_id": 2, "name": "Менеджер Проектов", "orders": 25, "paid": 4200000 }],
  "recent_orders": [],
  "overdue_orders": []
}
```

`monthly` всегда содержит 12 точек — последние 12 месяцев.

### `GET /dashboard/pricing`

Ставки, SLA и коэффициенты сложности:

```json
{
  "practices": [
    { "value": "it", "label": "IT-консалтинг", "rate": 6000, "sla_hours": 48 }
  ],
  "complexities": [{ "value": "standard", "label": "Стандартная", "multiplier": 1.25 }]
}
```

---

## Сотрудники

### `GET /users?role=manager`

Список активных сотрудников; `role` опционален. Используется для выбора менеджера.

---

## Бот (Telegram и VK)

Все методы требуют `X-Bot-Token`.

### `POST /bot/users`

```json
{ "telegram_id": 700000001, "username": "client_demo", "full_name": "Демо Клиент" }
```

Возвращает `BotRegisterOut` с ролью (`client`/`manager`) и признаком регистрации.

### `GET /bot/pricing`

Прайс и коэффициенты для расчёта в боте.

### `POST /bot/ai/intake`

ИИ-ветка BPMN: извлекает данные из свободного текста, классифицирует практику,
проверяет дубликаты, подбирает команду, считает стоимость/SLA и готовит черновик КП.
Заявку **не создаёт** — это делает бот после подтверждения клиента.

```json
{
  "telegram_id": 700000001,
  "text": "ООО «Вектор», нужен финансовый аудит, 40 часов, сложная задача, до 20.12.2026",
  "client_name": "Иван Петров"
}
```

Ответ (сокращённо):

```json
{
  "source": "ai",
  "title": "Финансовый аудит отчётности",
  "practice": "finance",
  "practice_label": "Финансовый консалтинг",
  "hours": 40,
  "complexity": "complex",
  "estimate": { "rate": 5000, "amount": 320000, "sla_hours": 24 },
  "duplicates": [],
  "team": [{ "full_name": "Сотрудник практики", "role_label": "Финансист" }],
  "sla_risk": "low",
  "kp": { "title": "Коммерческое предложение...", "text": "...", "amount": 320000 }
}
```

Если `POLZA_API_KEY` не задан или модель недоступна, возвращается
`source: "fallback"` — данные извлекаются правилами, endpoint продолжает работать.

### `POST /bot/orders`

```json
{
  "telegram_id": 700000001,
  "practice": "management",
  "title": "Стратегия развития на 2027 год",
  "description": "Нужна сессия с руководством",
  "hours": 24,
  "complexity": "standard",
  "client_name": "ООО «Ромашка»",
  "phone": "+7 900 000-00-00",
  "email": "client@example.ru"
}
```

Поле `kp` необязательное: если передать черновик КП из `/bot/ai/intake`,
он сохранится как документ `proposal` в карточке заявки.

Ответ `201`:

```json
{
  "id": 73,
  "number": "CF-2026-0073",
  "title": "Стратегия развития на 2027 год",
  "amount": 135000,
  "sla_due_at": "2026-03-03T09:00:00"
}
```

### `GET /bot/orders?telegram_id=...`

Заказы клиента (краткие карточки).

### `GET /bot/orders/{number}?telegram_id=...`

Детали заказа. Чужой заказ → `403`.

### `GET /bot/queue`

Очередь новых заявок для менеджера.

### `POST /bot/orders/{order_id}/status`

```json
{ "telegram_id": 700000002, "status": "qualified", "comment": "Взял в работу" }
```

Доступно только менеджеру.

### `GET /bot/stats?telegram_id=...`

Сводка: всего заказов, в работе, закрыто, сумма, просрочки.

### `POST /bot/link`

```json
{ "telegram_id": 700000002, "full_name": "Демо Менеджер" }
```

Ответ:

```json
{ "url": "http://localhost:5173/magic?token=eyJhbGciOi..." }
```

### `GET /bot/notifications?limit=50`

Недоставленные уведомления (outbox).

### `POST /bot/notifications/ack`

```json
{ "ids": [101, 102] }
```

Помечает уведомления доставленными.

### `GET /bot/health`

Проверка доступности API для бота.

---

## Прототип

Публичный демо-API для [UX/UI-прототипа](../frontend/public/prototype/README.md).
Включается флагом `PROTOTYPE_DEMO=true`; работает с теми же заявками, клиентами и
документами, что бот и дашборд. Авторизация для учебного стенда не требуется.

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/prototype/bootstrap?order_id=...` | список заявок, текущая заявка, справочники |
| `POST` | `/prototype/orders` | создать заявку |
| `POST` | `/prototype/orders/{id}/clarify` | задать вопрос клиенту |
| `POST` | `/prototype/orders/{id}/answer` | ответ клиента на уточнение |
| `POST` | `/prototype/orders/{id}/proposal` | сформировать и отправить КП |
| `POST` | `/prototype/orders/{id}/sign` | подписать КП (имитация) |
| `POST` | `/prototype/orders/{id}/remarks` | замечания клиента к КП |
| `POST` | `/prototype/orders/{id}/pay` | тестовая оплата картой и чек |
| `POST` | `/prototype/orders/{id}/contract` | сформировать договор |
| `POST` | `/prototype/orders/{id}/start` | начать работы |
| `POST` | `/prototype/orders/{id}/act` | сформировать акт |
| `POST` | `/prototype/orders/{id}/confirm-act` | подтвердить акт клиентом |
| `POST` | `/prototype/orders/{id}/practice` | изменить практику и консультанта |

Пример создания КП:

```json
{
  "solution": "Диагностика процесса и план оптимизации",
  "cost": 45000,
  "days": 5,
  "sla": "Ответ в течение 1 рабочего дня",
  "consultant": "Анна Смирнова"
}
```

Недопустимое действие возвращает `400` с текстом причины.

Тестовая оплата:

```json
{
  "card_number": "4111 1111 1111 1111",
  "holder": "IVAN PETROV",
  "expiry": "12/40",
  "cvc": "123"
}
```

Деньги не списываются; в базе сохраняются сумма, последние 4 цифры и документ
`payment`. Карта `4000 0000 0000 0002` имитирует отказ банка.

---


```bash
# 1. Вход
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@consultflow.ru","password":"admin12345"}' | jq -r .access_token)

# 2. Список новых заявок
curl -s "http://127.0.0.1:8000/api/orders?status=new&page_size=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.total'

# 3. Перевод в работу
curl -s -X POST http://127.0.0.1:8000/api/orders/1/status \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"qualified","comment":"Проверено"}' | jq '.status'

# 4. Генерация КП
curl -s -X POST http://127.0.0.1:8000/api/orders/1/documents \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"doc_type":"proposal"}' | jq '.payload.title'
```
