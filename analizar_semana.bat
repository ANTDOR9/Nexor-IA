@echo off
chcp 65001 >nul
REM ─────────────────────────────────────────────
REM  NEXOR IA · Doble clic para generar el reporte
REM  de la semana con el JSON más reciente de datos\
REM ─────────────────────────────────────────────
cd /d "%~dp0"
echo.
echo  NEXOR · Reporte semanal
echo  ¿Cumpliste el reto de la semana pasada?
set /p CUMPLI="  Escribe si / no / parcial (Enter para omitir): "
if "%CUMPLI%"=="" (
    python scripts\finanzas.py %*
) else (
    python scripts\finanzas.py --cumpli %CUMPLI% %*
)
echo.
pause
