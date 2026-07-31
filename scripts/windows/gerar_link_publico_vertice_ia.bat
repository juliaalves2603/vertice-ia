@echo off
title VERTICE IA - LINK PUBLICO TEMPORARIO

set LINK_PUBLICO=https://generally-vertical-green-doctrine.trycloudflare.com

echo.
echo ============================================
echo        VERTICE IA - LINK PUBLICO
echo ============================================
echo.
echo Link publico atual:
echo %LINK_PUBLICO%
echo.
echo Usuario: vertice
echo Senha: 262817
echo.
echo Antes de continuar, confirme que a VERTICE esta aberta em:
echo http://127.0.0.1:8000
echo.

where cloudflared >nul 2>nul

if errorlevel 1 (
    echo ERRO: cloudflared nao foi encontrado.
    echo Instale o Cloudflare Tunnel.
    pause
    exit /b
)

echo Abrindo link publico no navegador...
start "" "%LINK_PUBLICO%"

echo.
echo Gerando tunel publico temporario...
echo.
echo IMPORTANTE:
echo Se aparecer um link NOVO abaixo, use o link novo.
echo O trycloudflare muda quando o tunel reinicia.
echo.
echo Nao feche esta janela enquanto estiver usando o link.
echo.

cloudflared tunnel --url http://127.0.0.1:8000

pause
