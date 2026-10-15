@echo off
rem Crea el icono "WhatsApp IA" en el escritorio y el arranque con Windows.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_accesos.ps1"
timeout /t 5 >nul
