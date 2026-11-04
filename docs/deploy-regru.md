# Развёртывание ConsultFlow на VPS reg.ru

Инструкция для чистого Ubuntu 22.04/24.04. Весь сайт, API, PostgreSQL и VK-бот
запускаются в Docker; на сервере не нужно отдельно ставить Python, Node.js или
PostgreSQL.

## 1. Что получится

```text
Интернет
   │ 80/443
   ▼
Caddy (HTTPS, Let's Encrypt)
   ▼
frontend (Nginx: React SPA + /prototype + прокси /api)
   ▼
backend (FastAPI) ──▶ PostgreSQL
   ▲
   └── VK-бот (Long Poll) ──▶ VK API
                         └──▶ Polza.ai (ИИ)
```

Наружу открыты только `80` и `443`. База и backend не имеют публичных портов.

## 2. Требования

- VPS reg.ru с Ubuntu 22.04/24.04, SSH-доступ root;
- 1–2 ГБ RAM достаточно для демо (при 1 ГБ желателен swap 2 ГБ);
- домен или поддомен, например `consultflow.example.ru`;
- открытые порты `22`, `80`, `443` в firewall reg.ru;
- VK-сообщество с включёнными возможностями бота (см. [vk.md](vk.md)).

Если на сервере уже стоит ISPmanager/nginx на 80/443, сначала освободите эти
порты или настройте reverse proxy в панели. Проще чистый Ubuntu без панели.

## 3. DNS

В панели reg.ru для домена добавьте:

| Тип | Имя | Значение |
| --- | --- | --- |
| A | `@` или `consultflow` | публичный IPv4 сервера |
| AAAA | `@` или `consultflow` | IPv6, если он есть у VPS |

Проверка с домашнего компьютера:

```powershell
Resolve-DnsName consultflow.example.ru
```

Должен вернуться IP сервера. DNS может обновляться до нескольких часов.

## 4. Установка Docker

```bash
ssh root@IP_СЕРВЕРА

apt-get update
apt-get upgrade -y
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

docker --version
docker compose version
```

Если RAM 1 ГБ, добавьте swap:

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 5. Код и настройки

```bash
cd /opt
git clone https://github.com/Yato92/SPS-ConsultFlow.git
cd SPS-ConsultFlow
cp .env.example .env
chmod 600 .env
nano .env
```

Для production заполните:

```env
DOMAIN=consultflow.example.ru

POSTGRES_PASSWORD=длинный-случайный-пароль
SECRET_KEY=длинная-случайная-строка
BOT_API_TOKEN=длинный-случайный-токен
ADMIN_EMAIL=admin@example.ru
ADMIN_PASSWORD=сильный-пароль-администратора

FRONTEND_URL=https://consultflow.example.ru
CORS_ORIGINS=https://consultflow.example.ru

SEED_DEMO=true
PROTOTYPE_DEMO=true

VK_GROUP_ID=242938568
VK_TOKEN=токен-сообщества

AI_ENABLED=true
POLZA_API_KEY=ключ-polza
AI_MODEL=deepseek/deepseek-v4.1-flash-1017
```

Секреты можно сгенерировать так:

```bash
openssl rand -hex 32
```

Для `POSTGRES_PASSWORD` используйте hex-строку без символов `@`, `:`, `/` и `%`:
пароль подставляется в URL подключения к PostgreSQL.

Для реального проекта, а не демо, поставьте `SEED_DEMO=false` до первого запуска
и `PROTOTYPE_DEMO=false`, если публичный прототип не нужен.

`SEED_DEMO=true` создаёт демо-данные только в пустой базе. Если база уже создана,
смена `ADMIN_PASSWORD` не изменит существующий пароль.

## 6. Запуск

```bash
cd /opt/SPS-ConsultFlow
docker compose -f docker-compose.prod.yml --profile vk up -d --build
```

`--profile vk` включает VK-бота. Без него поднимутся только сайт, API и база.

Первая сборка занимает несколько минут. Проверка:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f caddy backend vk-bot
```

Ожидаемые строки в логах VK-бота:

```text
VK-бот запущен: сообщество ... Long Poll готов
```

Откройте `https://consultflow.example.ru`. Caddy сам получит HTTPS-сертификат,
если DNS уже указывает на сервер и порты 80/443 открыты.

## 7. Если что-то не работает

| Симптом | Что проверить |
| --- | --- |
| Caddy не получает сертификат | DNS, порты 80/443, `docker compose ... logs caddy` |
| Сайт открывается, API 502 | `docker compose ... logs backend`, healthcheck |
| Не пускает в дашборд | `ADMIN_EMAIL`/`ADMIN_PASSWORD`, база уже была создана |
| VK-бот молчит | `logs vk-bot`, `VK_TOKEN`, `VK_GROUP_ID`, возможности бота |
| Ошибка 912 VK | включите **Управление → Сообщения → Настройки для бота → Возможности ботов** |
| ИИ не отвечает | `POLZA_API_KEY`, доступ сервера к `polza.ai` |
| Telegram-бот не подключается | на российском VPS Telegram может быть недоступен; используйте VK |

Проверка API изнутри контейнера:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

Проверка контейнеров:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

## 8. Обновление

```bash
cd /opt/SPS-ConsultFlow
git pull
docker compose -f docker-compose.prod.yml --profile vk up -d --build
```

## 9. Резервные копии

Создайте каталог и делайте дамп:

```bash
mkdir -p /root/backups
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U consultflow consultflow | gzip \
  > /root/backups/consultflow-$(date +%F).sql.gz
```

Ежедневный cron:

```cron
0 3 * * * cd /opt/SPS-ConsultFlow && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U consultflow consultflow | gzip > /root/backups/consultflow-$(date +\%F).sql.gz
```

Восстановление в пустую базу:

```bash
gunzip -c /root/backups/consultflow-2026-11-04.sql.gz | \
docker compose -f docker-compose.prod.yml exec -T db psql -U consultflow -d consultflow
```

Храните копии не только на этом же сервере. Второй сервер reg.ru удобно
использовать как хранилище бэкапов:

```bash
rsync -av /root/backups/ root@SECOND_SERVER:/backups/consultflow/
```

## 10. Второй сервер

Для учебного проекта один сервер — нормально. Второй можно использовать так:

1. **Бэкапы и мониторинг** — самый простой и полезный вариант.
2. **Staging** — копия сайта на отдельном поддомене и отдельной базе.
3. **Отдельная БД** — только если серверы соединены приватной сетью
   (WireGuard/Tailscale). Не открывайте PostgreSQL в интернет.
4. **HA/балансировка** — для настоящей отказоустойчивости нужны балансировщик,
   общая БД и object storage; двух VPS для этого мало.

Не запускайте два экземпляра VK-бота на одном сообществе: Long Poll может
разделить события между ними, и часть сообщений потеряется.

## 11. Безопасность

- SSH-ключи вместо пароля, желательно отключить root-логин по паролю;
- firewall: только `22`, `80`, `443`;
- `.env` с правами `600`, не коммитить;
- сменить демо-пароли и `ADMIN_PASSWORD`;
- перевыпустить токены, которые публиковались в переписке;
- HTTPS обязателен: Caddy уже настроен;
- регулярно проверять `docker compose ... ps` и свободное место `df -h`.
