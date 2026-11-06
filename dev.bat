@echo off
title Aether Space — Vite Dev Server
echo ========================================================
echo   Starting Aether Space Development Mode (Vite + FastAPI)
echo   Frontend (Vite HMR): http://localhost:5173
echo   Backend (FastAPI):   http://localhost:8000
echo ========================================================
cd /d "%~dp0"
start "Aether FastAPI Backend" cmd /c "python main.py 8000"
start http://localhost:5173
npm run dev
pause

