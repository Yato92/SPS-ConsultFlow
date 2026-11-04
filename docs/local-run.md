# Локальный запуск на другом ноутбуке

Инструкция для Windows. Проект копируется целиком, но виртуальное окружение и
`node_modules` лучше не переносить — их нужно создать заново.

## 1. Что установить

- **Python 3.12+** — <https://www.python.org/downloads/windows/>
  При установке включите **Add Python to PATH**.
- **Node.js 20+** — <https://nodejs.org/>
- Больше ничего: Docker, PostgreSQL и MySQL для локальной демонстрации не нужны,
  проект использует SQLite.

Проверка в PowerShell:

```powershell
python --version
node --version
npm --version
```

## 2. Что скопировать

Скопируйте папку проекта, обязательно включив:

- `backend/` — код API;
- `bot/` — VK- и Telegram-бот;
- `frontend/` — сайт;
- `start-consultflow.cmd`, `start-vk-bot.cmd`;
- `.env` — токены и настройки;
- `backend/consultflow.db` — текущая база с заявками (если нужна история).

Не копируйте:

- `.venv-backend/`, `backend/.venv/` — привязка к старому пути и Python;
- `frontend/node_modules/` — тяжёлая папка, ставится заново;
- `.uv-cache/`, `.uv-python/`, `.tmp-*`.

Если `.env` не скопировался (скрытый файл), создайте его:

```powershell
Copy-Item .env.example .env
notepad .env
```

Для VK-бота нужны `VK_GROUP_ID`, `VK_TOKEN`, `POLZA_API_KEY` и `AI_ENABLED=true`.
`BOT_API_TOKEN` должен совпадать у backend и бота. Telegram-токен для VK-демо не
нужен.

## 3. Установка зависимостей

Откройте PowerShell в папке проекта:

```powershell
cd C:\путь\к\ConsultFlow-Lab

python -m venv .venv-backend
.\.venv-backend\Scripts\python.exe -m pip install --upgrade pip
.\.venv-backend\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv-backend\Scripts\python.exe -m pip install -r bot\requirements.txt

cd frontend
npm install
cd ..
```

Если PowerShell не даёт активировать окружение, активировать его не нужно:
команды выше уже используют `.venv-backend\Scripts\python.exe` напрямую.

## 4. Запуск

Сначала backend и сайт:

```text
start-consultflow.cmd
```

Скрипт откроет два окна:

- backend — `http://127.0.0.1:8000`;
- сайт — `http://127.0.0.1:5173`.

Через несколько секунд откроется прототип:

- <http://127.0.0.1:5173/prototype/>
- дашборд: <http://127.0.0.1:5173>

Ссылку в личный кабинет клиента бот берёт из `FRONTEND_URL` в `.env`. Если
открываете VK на телефоне в той же Wi-Fi-сети, укажите в `.env` адрес ноутбука:

```env
FRONTEND_URL=http://192.168.1.102:5173
```

Vite запускается с `--host 0.0.0.0`, поэтому телефон сможет открыть страницу.
При первом запуске Windows может спросить разрешение для Node.js — разрешите
доступ в частной сети. Если IP ноутбука изменился, обновите `FRONTEND_URL` и
перезапустите backend.

Затем, **не закрывая backend**, запустите VK-бота:

```text
start-vk-bot.cmd
```

Бот работает через Long Poll, публичный IP или домен ему не нужен — только
интернет и тот же `VK_TOKEN`.

Остановка: закройте окна консолей. Сначала можно закрыть бота, потом сайт и
backend.

## 5. Вход в дашборд

Администратор:

```text
admin@consultflow.ru
admin12345
```

Менеджер:

```text
a.ivanov@consultflow.ru
manager12345
```

Если база скопирована со старого ноутбука, пароли останутся прежними. Если база
создана заново, эти учётные записи появятся после первого запуска при
`SEED_DEMO=true`.

## 6. Важно про два ноутбука

- Не запускайте **один и тот же VK-токен** одновременно на двух компьютерах:
  сообщения начнут распределяться между двумя Long Poll-клиентами. Перед
  запуском на новом ноуте закройте VK-бота на старом. На одном компьютере второй
  экземпляр теперь блокируется файловой блокировкой `.vk_bot.lock`.
- То же для Telegram-бота: один токен — один запущенный экземпляр.
- `backend/consultflow.db` — обычный файл SQLite. Если скопировать его на новый
  ноут, заявки сохранятся. Если удалить — база создастся заново с демо-данными.
- Не копируйте `.env` в GitHub или в публичную папку.

## 7. Если что-то не запускается

| Симптом | Что сделать |
| --- | --- |
| `python` не найден | переустановить Python с **Add to PATH** |
| `start-consultflow.cmd` пишет про venv | выполнить шаги 3 заново |
| Порт 8000 занят | закрыть старый backend или перезагрузить ноут |
| Порт 5173 занят | закрыть старый Vite; он мог занять 5174 |
| Сайт открылся, API 500 | смотреть окно backend, проверить `.env` |
| VK-бот молчит | backend запущен, `VK_TOKEN` и `VK_GROUP_ID` верные, у сообщества включены возможности бота |
| ИИ не отвечает | `POLZA_API_KEY`, `AI_ENABLED=true`, интернет |
| Нет демо-данных | `SEED_DEMO=true`, удалить `backend/consultflow.db` и перезапустить |

Ручной запуск без `.cmd`:

```powershell
# терминал 1
cd backend
..\.venv-backend\Scripts\python.exe -m uvicorn app.main:app --port 8000

# терминал 2
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173

# терминал 3
cd bot
..\.venv-backend\Scripts\python.exe -m vk_bot.main
```
