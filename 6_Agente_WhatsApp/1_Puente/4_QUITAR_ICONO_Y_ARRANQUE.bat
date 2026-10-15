@echo off
rem Borra el icono del escritorio y el arranque con Windows. No borra el puente ni la sesion.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_accesos.ps1" -Quitar
timeout /t 5 >nul
