@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv-backend\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%backend\.venv\Scripts\python.exe"

if not exist "%PY%" goto no_python
if not exist "%ROOT%.env" goto no_env

cd /d "%ROOT%bot"
echo Starting ConsultFlow VK bot...
echo Make sure the backend is running on http://127.0.0.1:8000
echo.
"%PY%" -m vk_bot.main
echo.
echo VK bot stopped.
pause
exit /b 0

:no_python
echo.
echo Python virtual environment not found.
echo See README.md, section "Quick start" for setup instructions.
echo.
pause
exit /b 1

:no_env
echo.
echo .env not found. Copy .env.example to .env and set VK_TOKEN and VK_GROUP_ID.
echo.
pause
exit /b 1
