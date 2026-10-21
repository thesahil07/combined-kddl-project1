@echo off
echo ========================================================
echo Starting KDDL Talent Platform (Backend & Frontend)
echo ========================================================

echo Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "KDDL Backend (FastAPI)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Starting Vite Frontend on http://127.0.0.1:5173 ...
start "KDDL Frontend (Vite)" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo Both servers have been launched in separate windows!
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://127.0.0.1:5173/
echo ========================================================
pause
