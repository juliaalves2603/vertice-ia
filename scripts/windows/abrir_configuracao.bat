@echo off
cd /d "%~dp0backend"
if not exist .env copy .env.example .env >nul
notepad .env
