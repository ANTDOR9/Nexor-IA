@echo off
REM ─────────────────────────────────────────────
REM  NEXOR IA · Doble clic para generar el reporte
REM  de la semana con el JSON más reciente de datos\
REM ─────────────────────────────────────────────
cd /d "%~dp0"
python scripts\finanzas.py %*
echo.
pause
