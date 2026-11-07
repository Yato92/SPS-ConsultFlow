# ConsultFlow

**От заявки до акта — один процесс**

Цифровой продукт для автоматизации процесса обработки заказов на консалтинговые услуги.
Расчётно-графическая работа по дисциплине «Современные программные средства», вариант 4.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Telegram](https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)

---

## Содержание

- [О продукте](#о-продукте)
- [Возможности](#возможности)
- [UX/UI-прототип](#uxui-прототип)
- [Стек технологий](#стек-технологий)
- [Архитектура](#архитектура)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт](#быстрый-старт)
- [Запуск через Docker](#запуск-через-docker)
- [Демо-доступ](#демо-доступ)
- [Работа с Telegram-ботом](#работа-с-telegram-ботом)
- [Роли и права](#роли-и-права)
- [API](#api)
- [Тестирование](#тестирование)
- [Документация](#документация)
- [Ссылки](#ссылки)

---

## О продукте

Консалтинговая компания принимает заявки из разных каналов, вручную считает стоимость,
согласовывает коммерческие предложения и договоры, а затем теряет статусы в переписке.
ConsultFlow собирает весь цикл в один процесс:

1. **Заявка** — клиент оставляет её в Telegram-боте или менеджер создаёт в дашборде.
2. **Квалификация и расчёт** — система определяет направление практики, оценивает трудоёмкость,
   стоимость и срок реакции по SLA.
3. **КП и договор** — документы формируются автоматически по шаблонам.
4. **Работы и акт** — статусы двигаются по воронке, клиент и менеджер получают уведомления.
5. **Аналитика** — дашборд показывает оплаты, расходы, маржу, конверсию, загрузку менеджеров
   и просрочки SLA.

В основе — единое ядро на FastAPI и одна база данных: и бот, и сайт работают с одним API,
поэтому данные в Telegram и в дашборде всегда синхронны.

## Возможности

### Telegram-бот (`bot/`, aiogram 3)

- пошаговая заявка: направление → описание → часы → сложность → подтверждение;
- автоматический расчёт стоимости по ставкам практик и коэффициенту сложности;
- список «Мои заказы», карточка заказа, история статусов;
- менеджерская часть: очередь новых заявок, смена статуса, статистика;
- уведомления о новых заявках и смене статусов (очередь в БД, доставка ботом);
- `/link` — одноразовая ссылка на дашборд с автоматической авторизацией (magic-link);
- ИИ-консультант на Polza.ai: свободные вопросы, контекст своих заявок и тарифов,
  подсказки по выбору практики (включается ключом `POLZA_API_KEY`).

### Дашборд (`frontend/`, React 18 + TypeScript + Ant Design)

- KPI: заказы, оплаты, расходы, финансовый результат, конверсия, просрочки SLA;
- графики: динамика по месяцам, структура оплат по практикам, воронка статусов;
- реестр заказов с фильтрами по статусу, направлению, менеджеру и периоду;
- карточка заказа: финансы, клиент, история, документы, смена статуса;
- справочник клиентов и страница Telegram-бота (пользователи, уведомления, инструкция);
- экспорт реестра в CSV, адаптивная вёрстка, тёмная тема не требуется.

### Backend (`backend/`, FastAPI + SQLAlchemy 2)

- REST API, OpenAPI/Swagger «из коробки»;
- JWT-авторизация сотрудников и magic-link для входа из бота;
- ролевая модель: администратор, менеджер, консультант, юрист, финансист;
- конечный автомат статусов с проверкой допустимых переходов и журналом аудита;
- расчёт стоимости, SLA и маржи; генерация документов (заявка, КП, договор, акт);
- ИИ-разбор входящей заявки: извлечение данных, проверка дубликатов,
  классификация практики, подбор команды, расчёт стоимости/SLA и черновик КП;
- outbox-очередь уведомлений для бота;
- SQLite по умолчанию, PostgreSQL — в docker-compose.

## UX/UI-прототип

Для защиты и демонстрации пути заявки сделан отдельный лёгкий макет на три экрана:
«Заявки», «Карточка заявки», «Кабинет клиента». Он встроен в frontend и работает
с общей базой данных через API `/api/prototype`: заявки, статусы, КП, тестовая
оплата и документы сохраняются и видны в VK-боте и React-дашборде.

Запустите backend и frontend, затем откройте
<http://127.0.0.1:5173/prototype/>. Исходники —
[frontend/public/prototype/](frontend/public/prototype/).

Переключатель «Сотрудник / Клиент» показывает обе роли на одной и той же заявке,
поэтому замечания, подписание КП и подтверждение акта сразу видны с обеих сторон.
В роли сотрудника в список попадают и реальные заявки из VK/Telegram, в роли
клиента — только демонстрационная лента. Подробнее —
[frontend/public/prototype/README.md](frontend/public/prototype/README.md).

### Личный кабинет клиента

Заявки из VK-бота видны сотруднику и в React-дашборде, и в прототипе в режиме
«Сотрудник». Клиент получает персональную ссылку вида
`http://<адрес-сайта>/client?token=...`. Ссылка подписана, действует 7 дней и
показывает только заявки этого клиента: статус, сумму, срок и документы.
В режиме «Клиент» прототипа чужие заявки не показываются.

## Стек технологий

| Слой | Технологии |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.1, Pydantic v2, PyJWT, pwdlib (Argon2), Uvicorn |
| База данных | SQLite (разработка), PostgreSQL 15 (Docker), внешняя MySQL 5.7/PostgreSQL |
| Telegram-бот | aiogram 3.31, httpx, pydantic-settings |
| Frontend | React 18, TypeScript 5.7, Vite 6, Ant Design 5, React Query 5, Axios, Recharts, dayjs |
| Инфраструктура | Docker, docker-compose, Nginx |
| Тестирование | pytest, httpx TestClient, TypeScript (`tsc --noEmit`), сборка Vite |

## Архитектура

```
                    ┌──────────────────────────┐
   Telegram         │        aiogram 3         │
   клиент/менеджер  │        bot/              │
                    └────────────┬─────────────┘
                                 │ HTTP + X-Bot-Token
                                 ▼
   Браузер          ┌──────────────────────────┐        ┌──────────────────┐
   сотрудник  ─────▶│   FastAPI backend/       │───────▶│  SQLite /        │
   (React SPA)      │   REST /api, JWT, роли   │        │  PostgreSQL 15   │
                    └──────────────────────────┘        └──────────────────┘
                       │            │
                       │            └── outbox уведомлений → бот (polling 5 c)
                       └── документы, расчёты, аудит, аналитика
```

- **Единый API.** Бот и SPA не дублируют бизнес-логику: расчёты, статусы и документы живут в backend.
- **Уведомления через outbox.** Backend не зависит от доступности Telegram: сообщения складываются
  в таблицу `notifications`, бот забирает их и подтверждает доставку.
- **Magic-link.** Бот выпускает короткоживущий JWT, дашборд обменивает его на обычный токен доступа.

Подробнее: [docs/architecture.md](docs/architecture.md).

## Структура репозитория

```
ConsultFlow-Lab/
├── backend/               # FastAPI-приложение
│   ├── app/
│   │   ├── api/           # роутеры: auth, orders, clients, analytics, users, bot, telegram
│   │   ├── core/          # конфигурация, безопасность, перечисления, утилиты
│   │   ├── services/      # заказы, цены, документы, аналитика
│   │   ├── models.py      # SQLAlchemy-модели
│   │   ├── schemas.py     # Pydantic-схемы
│   │   ├── seed.py        # демо-данные (76 заказов, 14 клиентов, 6 сотрудников)
│   │   └── main.py        # точка входа, CORS, lifespan
│   ├── tests/             # pytest: 49 тестов
│   ├── Dockerfile
│   └── requirements.txt
├── bot/                   # Telegram-бот
│   ├── consultflow_bot/
│   │   ├── handlers/      # заявки, мои заказы, менеджер, fallback
│   │   ├── api.py         # клиент backend
│   │   ├── views.py       # тексты сообщений
│   │   ├── keyboards.py   # клавиатуры
│   │   ├── notifications.py
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # React SPA
│   ├── public/prototype/  # интерактивный UX/UI-макет на 3 экрана (HTML + API)
│   ├── src/
│   │   ├── api/           # axios-клиент, типы, React Query hooks
│   │   ├── auth/          # контекст авторизации
│   │   ├── components/    # layout, карточки, статусы, графики
│   │   ├── pages/         # Login, Dashboard, Orders, Clients, Telegram
│   │   └── styles/
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                  # архитектура, API, BPMN, тестирование
├── consultflow-wiki/      # продуктовые артефакты РГР
├── dashboard/             # учебный Dash-дашборд из предыдущей лабораторной
├── docker-compose.yml
├── .env.example
└── README.md
```

## Быстрый старт

Требования: **Python 3.12+**, **Node.js 20+** и npm. Telegram-токен для локального запуска не обязателен:
без него поднимаются backend и дашборд, а бот запускается после добавления токена.

Если нужно перенести проект на другой ноутбук и запустить без Docker:
[docs/local-run.md](docs/local-run.md).

### Самый простой запуск на Windows

Если зависимости уже установлены, дважды щёлкните
[start-consultflow.cmd](start-consultflow.cmd): скрипт откроет backend и frontend
в двух окнах и запустит браузер с прототипом.

Чтобы остановить приложение, закройте оба окна консоли.

### 1. Клонирование и окружение

```powershell
git clone https://github.com/Yato92/SPS-ConsultFlow.git
cd SPS-ConsultFlow
Copy-Item .env.example .env
```

Файл `.env` лежит в корне и читается и backend-ом, и ботом. Для локального запуска его можно не менять.

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API: <http://127.0.0.1:8000/api>
- Swagger: <http://127.0.0.1:8000/docs>
- Проверка: <http://127.0.0.1:8000/health>

При первом старте база создаётся автоматически и наполняется демо-данными (76 заказов).
Если база уже есть, повторное наполнение не выполняется.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Откройте <http://127.0.0.1:5173>. Vite проксирует `/api` на `http://127.0.0.1:8000`,
поэтому отдельная настройка CORS для разработки не нужна.

Production-сборка:

```powershell
npm run build      # tsc --noEmit + vite build → dist/
npm run preview    # локальный просмотр собранного приложения
```

### 4. Telegram-бот (после получения токена)

1. Создайте бота у [@BotFather](https://t.me/BotFather) и скопируйте токен.
2. В корневом `.env` укажите:

```env
BOT_TOKEN=123456789:AA...ваш-токен
MANAGER_TELEGRAM_IDS=ваш_telegram_id
```

Свой ID можно узнать командой `/id` в боте или у [@userinfobot](https://t.me/userinfobot).

3. Установите зависимости и запустите бота:

```powershell
pip install -r bot/requirements.txt
cd bot
python run.py
```

Или дважды щёлкните [start-bot.cmd](start-bot.cmd) — но backend уже должен быть запущен.
Если бот запустился, в консоли появится строка `ConsultFlow-бот запущен: @...`.

Бот читает тот же `.env` из корня проекта и обращается к backend по `BACKEND_URL`
(по умолчанию `http://127.0.0.1:8000`).

#### Если Telegram не подключается

Ошибка `ClientConnectorError ... api.telegram.org:443` означает, что компьютер не
может открыть соединение с Telegram. Код и токен здесь ни при чём.

Проверка:

```powershell
Test-NetConnection api.telegram.org -Port 443
```

Если `TcpTestSucceeded : False`, нужен VPN или прокси:

- **VPN** — включите его до запуска `start-bot.cmd`;
- **прокси** — добавьте в `.env` строку и перезапустите бота:

```env
TELEGRAM_PROXY=socks5://127.0.0.1:1080
# или http://user:password@host:port
```

Для прокси уже добавлена зависимость `aiohttp-socks` в
`bot/requirements.txt`. Не используйте случайные публичные прокси: через них
проходит токен бота.

### ИИ-консультант и AI-заявка

Чтобы бот отвечал на свободные вопросы, добавьте в `.env` ключ Polza.ai:

```env
POLZA_API_KEY=ваш-ключ
AI_MODEL=deepseek/deepseek-v4.1-flash-1017
```

Ключ создаётся в [личном кабинете Polza.ai](https://polza.ai/dashboard/api-keys).
После перезапуска бота в меню появится «🤖 Спросить ИИ». Кнопка
**«✨ AI-заявка»** запускает BPMN-ветку: ИИ извлекает данные из свободного
текста, проверяет дубликаты, определяет практику и команду, считает стоимость
и SLA, готовит черновик КП. Заявка создаётся после подтверждения клиента.
Подробнее — [docs/ai.md](docs/ai.md).

### VK-бот

Второй канал на случай, если Telegram недоступен. Работает через Bots Long Poll
сообщества, без публичного вебхука.

1. Создайте сообщество ВКонтакте, включите сообщения и в
   **Управление → Сообщения → Настройки для бота** поставьте
   **Возможности ботов → Включены**.
2. В **Управление → Дополнительно → Работа с API** создайте токен с правами
   `messages` и `manage`, включите Long Poll API с событием `message_new`.
3. Добавьте в `.env`:

```env
VK_GROUP_ID=123456789
VK_TOKEN=токен-сообщества
```

4. Запустите backend, затем [start-vk-bot.cmd](start-vk-bot.cmd).
5. Напишите сообществу `/start`.

Клиент может работать с заявкой прямо в VK: открыть карточку в «Мои заявки»,
прочитать документы, подписать КП, отправить замечания, провести тестовую
оплату и подтвердить работу. Сотрудник меняет статус кнопками в «Очереди
заявок» или в дашборде — клиенту приходит уведомление с кнопкой заявки.

Подробная настройка, ограничения и разбор ошибок — [docs/vk.md](docs/vk.md).

## Запуск через Docker

```powershell
docker compose up --build
```

Поднимаются PostgreSQL, backend и frontend (Nginx):

- дашборд: <http://localhost:8080>
- API: <http://localhost:8000/api>
- Swagger: <http://localhost:8000/docs>

Бот вынесен в отдельный профиль, чтобы стек запускался без токена:

```powershell
$env:BOT_TOKEN="123456789:AA..."
docker compose --profile bot up --build
```

Остановка: `docker compose down`, удаление данных: `docker compose down -v`.

### Production на VPS

Для reg.ru и любого Ubuntu-сервера есть отдельный стек с Caddy, HTTPS и
VK-ботом:

```bash
cp .env.example .env
# заполните DOMAIN, POSTGRES_PASSWORD, SECRET_KEY, BOT_API_TOKEN,
# ADMIN_PASSWORD, VK_GROUP_ID, VK_TOKEN и POLZA_API_KEY
docker compose -f docker-compose.prod.yml --profile vk up -d --build
```

Подробная инструкция: [docs/deploy-regru.md](docs/deploy-regru.md).

Если база уже создана на reg.ru (MySQL 5.7 или PostgreSQL), добавьте
`DATABASE_URL` в `.env` и запустите stack с внешней БД:

```bash
docker compose -f docker-compose.prod.yml \
  -f docker-compose.external-db.yml --profile vk up -d --build
```

Проверка: `curl https://ваш-домен/health/db`. Подробности:
[docs/database-regru.md](docs/database-regru.md).

## Демо-доступ

| Роль | E-mail | Пароль |
| --- | --- | --- |
| Администратор | `admin@consultflow.ru` | `admin12345` |
| Менеджер | `manager@consultflow.ru` | `manager12345` |
| Консультант | `consultant@consultflow.ru` | `consultant12345` |
| Юрист | `lawyer@consultflow.ru` | `lawyer12345` |
| Финансист | `finance@consultflow.ru` | `finance12345` |

Демо-доступ подставляется на странице входа одной кнопкой. Логин и пароль администратора
можно переопределить переменными `ADMIN_EMAIL` и `ADMIN_PASSWORD`.

## Работа с Telegram-ботом

| Команда | Назначение |
| --- | --- |
| `/start` | регистрация, выбор роли и главное меню |
| `/menu` | вернуться в меню |
| `/new` | создать заявку |
| `/orders` | мои заказы (для менеджера — очередь) |
| `/stats` | сводка по заказам |
| `/link` | одноразовая ссылка на дашборд |
| `/id` | показать Telegram ID |
| `/cancel` | отменить заполнение |

Сценарий клиента:

1. `/start` → «Оставить заявку».
2. Выбрать направление (менеджмент, финансы, право, ИТ).
3. Описать задачу, указать часы и сложность.
4. Подтвердить — бот покажет номер заказа, стоимость и срок реакции.

Сценарий менеджера:

1. Менеджер получает уведомление о новой заявке.
2. В разделе «Очередь заявок» открывает карточку и переводит её по статусам.
3. При переходе в «КП отправлено», «Договор подписан», «Работы выполнены»
   документ формируется автоматически.
4. `/link` открывает дашборд с уже выполненным входом.

## Роли и права

| Роль | Дашборд | Заказы | Документы | Пользователи |
| --- | --- | --- | --- | --- |
| `admin` | полный доступ | создание, изменение, любые статусы | генерация и подписание | управление |
| `manager` | полный доступ к операциям | создание, изменение, статусы | генерация и подписание | — |
| `consultant` | чтение | просмотр | просмотр | — |
| `lawyer` | чтение | просмотр | просмотр | — |
| `finance` | чтение + финансы | просмотр | просмотр | — |

Бот различает роли `client` и `manager`: менеджеры получают уведомления и доступ к очереди заявок.

## API

Все методы доступны по префиксу `/api`. Авторизация — `Authorization: Bearer <JWT>`;
методы бота — заголовок `X-Bot-Token`.

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `POST` | `/auth/login` | вход по e-mail и паролю |
| `POST` | `/auth/magic` | обмен magic-link на токен |
| `GET` | `/auth/me` | текущий пользователь |
| `GET` | `/dashboard` | KPI, графики, воронка, последние заказы |
| `GET` | `/dashboard/pricing` | ставки, SLA и коэффициенты |
| `GET` | `/orders` | реестр с фильтрами и пагинацией |
| `POST` | `/orders` | создание заказа |
| `GET` | `/orders/{id}` | карточка заказа |
| `PATCH` | `/orders/{id}` | изменение полей |
| `POST` | `/orders/{id}/status` | смена статуса |
| `POST` | `/orders/{id}/documents` | генерация документа |
| `POST` | `/orders/{id}/documents/{doc_id}/sign` | подписание |
| `GET` | `/orders/export` | экспорт CSV |
| `GET` | `/clients` | справочник клиентов |
| `GET` | `/users/managers` | список менеджеров |
| `GET` | `/bot/orders` | заказы для бота |
| `POST` | `/bot/orders` | заявка из бота |
| `POST` | `/bot/link` | magic-link для дашборда |
| `GET` | `/bot/notifications` | очередь уведомлений |
| `POST` | `/bot/notifications/{id}/ack` | подтверждение доставки |

Полное описание с примерами: [docs/api.md](docs/api.md), интерактивно — `/docs`.

## Тестирование

```powershell
cd backend
..\.venv-backend\Scripts\python.exe -m pytest
```

- 49 тестов: авторизация, права доступа, статусы, документы, аналитика, бот, расчёты, ИИ-разбор и сценарии прототипа;
- отдельная тестовая БД, детерминированные фикстуры;
- проверка типов и сборки фронтенда: `cd frontend && npm run build`;
- браузерные сценарии прототипа проверены в headless Edge.

Матрица проверок и ручные сценарии: [docs/testing.md](docs/testing.md).

## Документация

- [docs/architecture.md](docs/architecture.md) — компоненты, модель данных, безопасность;
- [docs/api.md](docs/api.md) — описание REST API и примеры запросов;
- [docs/bpmn.md](docs/bpmn.md) — процесс «как есть / как должно быть», статусы и SLA;
- [docs/testing.md](docs/testing.md) — программа и результаты тестирования;
- [docs/local-run.md](docs/local-run.md) — перенос и локальный запуск на другом ноутбуке;
- [docs/ai.md](docs/ai.md) — Polza.ai, ИИ-консультант и AI-разбор заявки (BPMN);
- [docs/vk.md](docs/vk.md) — VK-бот: Long Poll, настройка сообщества и ограничения;
- [docs/deploy-regru.md](docs/deploy-regru.md) — production-развёртывание на VPS reg.ru;
- [docs/database-regru.md](docs/database-regru.md) — подключение внешней MySQL/PostgreSQL reg.ru;
- [frontend/public/prototype/README.md](frontend/public/prototype/README.md) — как открыть интерактивный макет и пройти оба сценария;
- [consultflow-wiki/](consultflow-wiki/) — продуктовые артефакты РГР (роли, состояние, развитие).

## Ссылки

- Репозиторий: <https://github.com/Yato92/SPS-ConsultFlow>
- Wiki проекта: [consultflow-wiki/Home.md](consultflow-wiki/Home.md)
- Swagger (локально): <http://127.0.0.1:8000/docs>
- Дашборд (локально): <http://127.0.0.1:5173>

---

**Автор:** студент группы 5ИТб-1 · КнАГУ
**Дисциплина:** «Современные программные средства», 2026
