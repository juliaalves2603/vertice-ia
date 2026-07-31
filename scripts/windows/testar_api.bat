@echo off
echo Testando VERTICE IA LIMPA...
powershell -ExecutionPolicy Bypass -Command "Invoke-RestMethod 'http://127.0.0.1:8000/api/status'"
pause
