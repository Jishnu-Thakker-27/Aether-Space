@echo off
title Aether Space — FastAPI + Vite AI Assistant
echo ========================================================
echo   Starting Aether Space Server (FastAPI + Vite)
echo   FastAPI Backend on http://127.0.0.1:8000
echo   API Documentation on http://127.0.0.1:8000/docs
echo ========================================================
cd /d "%~dp0"
start http://127.0.0.1:8000
python main.py 8000
pause
