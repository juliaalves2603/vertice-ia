@echo off
setlocal
cd /d "%~dp0"
set "DESTINO=%~dp0_BACKUP_FUNCIONANDO"
echo Criando backup em:
echo %DESTINO%
xcopy "%~dp0" "%DESTINO%\" /E /I /Y /EXCLUDE:backup_exclude.txt
echo.
echo Backup criado.
pause
