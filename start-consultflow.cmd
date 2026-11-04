@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv-backend\Scripts\python.exe"
if not exist "%PY%" set "PY=%ROOT%backend\.venv\Scripts\python.exe"
if not exist "%PY%" goto no_python
if not exist "%ROOT%frontend\node_modules" goto no_node

echo Starting ConsultFlow...
start "ConsultFlow Backend" /D "%ROOT%backend" "%PY%" -m uvicorn app.main:app --port 8000
start "ConsultFlow Frontend" /D "%ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"

echo Waiting for backend and frontend...
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:5173/prototype/"

echo.
echo Prototype: http://127.0.0.1:5173/prototype/
echo Close both console windows to stop the application.
echo.
pause
exit /b 0

:no_python
echo.
echo Python virtual environment not found.
echo See README.md, section "Quick start" for setup instructions.
echo.
pause
exit /b 1

:no_node
echo.
echo Frontend dependencies not found.
echo Run "npm install" in the frontend folder first.
echo.
pause
exit /b 1

