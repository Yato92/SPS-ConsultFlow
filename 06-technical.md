# 2. Техническая часть

## 2.1 Программные требования

- ОС сервера: Ubuntu 22.04 LTS
- СУБД: PostgreSQL 15
- Backend: Python 3.11 + FastAPI
- Frontend: React 18 + TypeScript
- Очередь: RabbitMQ
- Кэш: Redis 7
- Контейнеризация: Docker + Kubernetes
- CI/CD: GitLab CI

## 2.2 Аппаратные требования

| Компонент | Минимум    | Рекомендуется |
| --------- | ---------- | ------------- |
| CPU       | 4 vCPU     | 8 vCPU        |
| RAM       | 8 ГБ       | 16 ГБ         |
| Диск      | 100 ГБ SSD | 250 ГБ SSD    |
| Сеть      | 100 Мбит/с | 1 Гбит/с      |

## 2.3 Описание архитектуры

ConsultFlow построен по микросервисной архитектуре:

- **API Gateway** — единая точка входа.
- **Order Service** — приём и обработка заявок.
- **Routing Service** — маршрутизация по практикам.
- **Pricing Service** — расчёт стоимости и сроков.
- **Document Service** — генерация договоров и актов.
- **Notification Service** — уведомления.
- **Analytics Service** — KPI и отчёты.

Схема: [C4-диаграмма контейнеров](artifacts/c4-containers.png)

## 2.4 Схемы баз данных

Основные сущности:

- `clients` — клиенты
- `orders` — заказы
- `order_status_history` — история статусов
- `consultants` — консультанты
- `practices` — практики
- `contracts` — договоры
- `acts` — акты
- `users` — пользователи
- `roles` — роли

Схема: [ER-диаграмма](artifacts/er-diagram.png)

## 2.5 Интеграции

- 1С: бухгалтерия и договоры
- CRM: заявки и клиенты
- Email/SMTP: уведомления
- Telegram-бот: оповещения менеджеров

## 2.6 Мониторинг

- Prometheus + Grafana
- Loki для логов
- Alertmanager для алертов
