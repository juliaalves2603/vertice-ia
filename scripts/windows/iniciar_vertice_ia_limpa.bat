@echo off
title VERTICE IA LIMPA - DADOS REAIS
cd /d "%~dp0backend"
if not exist .env copy .env.example .env >nul
if not exist .venv (
  echo Criando ambiente Python...
  python -m venv .venv
)
call .venv\Scripts\activate
echo Instalando/checando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo ==========================================
echo VERTICE IA LIMPA rodando em:
echo http://127.0.0.1:8000
echo ==========================================
echo.
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
