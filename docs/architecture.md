# Архитектура ConsultFlow

Документ описывает устройство решения: компоненты, модель данных, бизнес-правила,
безопасность и варианты развёртывания.

## 1. Компоненты

| Компонент | Расположение | Ответственность |
| --- | --- | --- |
| Telegram-бот | `bot/` | интерфейс клиента и менеджера, сбор заявки, уведомления, magic-link |
| Backend API | `backend/` | бизнес-логика, права, расчёты, документы, аудит, аналитика |
| SPA-дашборд | `frontend/` | визуализация показателей, работа с заказами и клиентами |
| База данных | SQLite / PostgreSQL | единое хранилище заказов, клиентов, событий, документов |
| Nginx | `frontend/nginx.conf` | раздача статики и проксирование `/api` |
| Docker Compose | `docker-compose.yml` | локальное развёртывание всего контура |

Ключевое решение: **бот и SPA — тонкие клиенты**. Они не содержат правил расчёта стоимости,
допустимых переходов статусов и шаблонов документов, а вызывают один и тот же API.
Это исключает расхождение данных между каналами.

```
Telegram ──▶ aiogram ──┐
                       ├──▶ FastAPI /api ──▶ SQLAlchemy ──▶ SQLite/PostgreSQL
Браузер ──▶ React SPA ─┘          │
                                  ├── services/orders.py     (жизненный цикл)
                                  ├── services/pricing.py    (ставки, SLA)
                                  ├── services/documents.py  (шаблоны документов)
                                  ├── services/analytics.py  (агрегаты дашборда)
                                  └── notifications (outbox) ──▶ бот
```

## 2. Потоки данных

### 2.1 Заявка из Telegram

1. Бот вызывает `POST /api/bot/users` при `/start`, создавая `BotUser`.
2. Клиент заполняет форму; бот вызывает `GET /api/bot/pricing` для подсказки расчёта
   и `POST /api/bot/orders` для создания заказа.
3. Backend создаёт `Client` (если новый), `Order`, событие `OrderEvent`, документ-заявку
   и записи в `Notification` для менеджеров.
4. Бот раз в 5 секунд забирает `GET /api/bot/notifications`, отправляет сообщения
   и подтверждает доставку через `POST /api/bot/notifications/ack`.

### 2.2 Вход в дашборд из бота

1. Бот вызывает `POST /api/bot/link` со своим `telegram_id`.
2. Backend выпускает JWT с типом `magic` и сроком 15 минут, возвращает ссылку
   `{FRONTEND_URL}/magic?token=...`.
3. SPA обменивает токен через `POST /api/auth/magic` на обычный access-токен (12 часов)
   и сохраняет его в `localStorage`.

### 2.3 Смена статуса в дашборде

1. Менеджер вызывает `POST /api/orders/{id}/status`.
2. Backend проверяет переход по `STATUS_TRANSITIONS`, пишет `OrderEvent` и `AuditLog`.
3. При необходимости формируется документ (`document_for_status`).
4. Создаются уведомления клиенту и менеджерам — их доставит бот.

## 3. Модель данных

| Таблица | Назначение | Ключевые поля |
| --- | --- | --- |
| `users` | сотрудники | `email`, `password_hash`, `role`, `is_active` |
| `clients` | компании-клиенты | `name`, `contact_person`, `phone`, `email`, `telegram_id` |
| `orders` | заказы | `number`, `title`, `practice`, `status`, `amount`, `paid_amount`, `expenses`, `hours`, `complexity`, `sla_due_at`, `deadline`, `manager_id`, `client_id`, `source` |
| `order_events` | история статусов | `order_id`, `from_status`, `to_status`, `actor_type`, `actor_id`, `comment` |
| `documents` | документы | `order_id`, `doc_type`, `number`, `payload` (JSON), `status` |
| `bot_users` | пользователи Telegram | `telegram_id`, `username`, `role`, `user_id` |
| `notifications` | outbox для бота | `recipient`, `text`, `status`, `created_at`, `sent_at` |
| `audit_logs` | журнал действий | `actor_id`, `action`, `entity`, `entity_id`, `payload` |

Связи: `Client 1—N Order`, `User (manager) 1—N Order`, `Order 1—N OrderEvent`,
`Order 1—N Document`, `BotUser 1—0..1 User`.

Номер заказа формируется как `CF-{год}-{порядковый номер}` и уникален.

## 4. Жизненный цикл заказа

```
new → qualified → proposal → approved → contract → in_progress → done → closed
        │            │           │           │            │
        └────────────┴───────────┴───────────┴────────────┴──▶ cancelled
```

- Переходы ограничены словарём `STATUS_TRANSITIONS`; недопустимый переход возвращает `409`.
- `cancelled` возможен на любом этапе, кроме `done` и `closed`.
- Администратор может принудительно установить статус (с записью в аудит).
- Каждый переход создаёт событие с автором (`user`, `bot`, `system`) и комментарием.

Подробная BPMN-схема и SLA: [bpmn.md](bpmn.md).

## 5. Расчёт стоимости и SLA

| Направление | Ставка, ₽/час | SLA первичной обработки |
| --- | --- | --- |
| Управленческий консалтинг | 4 500 | 48 ч |
| Финансовый консалтинг | 5 000 | 24 ч |
| Юридический консалтинг | 5 500 | 72 ч |
| IT-консалтинг | 6 000 | 48 ч |

Стоимость: `ставка × часы × коэффициент сложности`.

| Сложность | Коэффициент |
| --- | --- |
| Базовая | 1.0 |
| Стандартная | 1.25 |
| Сложная | 1.6 |

`SLA` фиксируется в `orders.sla_due_at` при создании и при смене статуса.
Просрочка вычисляется свойством `is_overdue` (активные статусы, срок в прошлом).

## 6. Документы

Шаблоны находятся в `backend/app/services/documents.py`. Документ содержит заголовок,
номер, текст и метаданные; тип определяется статусом:

| Статус | Документ |
| --- | --- |
| `new` | Заявка |
| `proposal` | Коммерческое предложение |
| `contract` | Договор |
| `done` | Акт выполненных работ |

Документ можно сформировать вручную из карточки заказа или в боте. Подписание меняет
статус документа на `signed` и фиксируется в аудите.

## 7. Безопасность

- Пароли хранятся как Argon2-хэш (`pwdlib`), необратимо.
- Сотрудники получают JWT (`HS256`, 12 часов) с полями `sub`, `role`, `type`.
- Magic-link — отдельный тип токена с коротким сроком жизни и одноразовым использованием
  на уровне обмена (повторный обмен возможен только до истечения срока).
- Бот авторизуется заголовком `X-Bot-Token`, значение задаётся в `.env`.
- Ролевая модель проверяется зависимостями FastAPI (`require_roles`), а не только UI.
- CORS ограничен списком `CORS_ORIGINS`.
- Все изменения заказов попадают в `audit_logs`.
- Секреты не хранятся в репозитории: используется `.env`, шаблон — `.env.example`.

## 8. Конфигурация

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./consultflow.db` | строка подключения |
| `SECRET_KEY` | dev-значение | подпись JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 720 | срок жизни access-токена |
| `MAGIC_LINK_EXPIRE_MINUTES` | 15 | срок жизни magic-link |
| `CORS_ORIGINS` | localhost:5173, :8050 | разрешённые источники |
| `FRONTEND_URL` | `http://localhost:5173` | база для magic-link |
| `SEED_DEMO` | `true` | наполнение демо-данными |
| `BOT_API_TOKEN` | dev-значение | токен бота для API |
| `MANAGER_TELEGRAM_IDS` | пусто | ID менеджеров в Telegram |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | demo | учётная запись администратора |

## 9. Развёртывание

### Локально

- backend: `uvicorn app.main:app --reload --port 8000`;
- frontend: `npm run dev` (Vite проксирует `/api`);
- bot: `python run.py`;
- БД: SQLite-файл рядом с backend.

### Docker

`docker-compose.yml` поднимает PostgreSQL 15, backend, frontend (Nginx) и — отдельным
профилем — бота. Nginx проксирует `/api` на `backend:8000`, SPA отдаётся с fallback
на `index.html` для клиентского роутинга.

## 10. Ограничения и развитие

- Уведомления доставляются polling-ом (5 с), а не webhook — проще для учебного контура;
  для production достаточно заменить воркер на webhook.
- Нет загрузки файлов: документы формируются как текст и экспортируются в файл.
- Аналитика считается на лету; при росте данных потребуются материализованные агрегаты.
- Резервное копирование в docker-контуре — через volume `pgdata`.
