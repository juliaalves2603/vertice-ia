@echo off
title VERTICE IA - MODO APRESENTACAO

cd /d "%~dp0"

echo.
echo ============================================
echo        VERTICE IA - MODO APRESENTACAO
echo ============================================
echo.
echo Usuario: vertice
echo Senha: 262817
echo.
echo Abrindo servidor local da VERTICE IA...
echo.

start "VERTICE IA - SERVIDOR LOCAL" cmd /k "cd /d "%~dp0" && call iniciar_vertice_ia.bat"

echo.
echo Aguardando o servidor iniciar...
timeout /t 8 /nobreak >nul

echo.
echo Abrindo login local...
start "" "http://127.0.0.1:8000/login"

echo.
echo Verificando Cloudflare Tunnel...
where cloudflared >nul 2>nul

if errorlevel 1 (
    echo.
    echo ERRO: cloudflared nao foi encontrado.
    echo Instale ou rode manualmente o Cloudflare Tunnel.
    echo.
    pause
    exit /b
)

echo.
echo Gerando link publico temporario...
echo.
echo Copie o link que aparecer abaixo:
echo https://....trycloudflare.com
echo.
echo Usuario: vertice
echo Senha: 262817
echo.
echo IMPORTANTE:
echo Deixe esta janela e a janela do servidor abertas.
echo Se fechar, o link publico para de funcionar.
echo.

cloudflared tunnel --url http://127.0.0.1:8000

pause
