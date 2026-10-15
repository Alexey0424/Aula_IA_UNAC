@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Puente WhatsApp - Cloudflare
rem Prende el puente y abre el panel. Si ya estaba prendido, solo abre el panel.
rem Con Windows arranca minimizado y sin navegador (argumento --sin-navegador).
where node >nul 2>nul || (echo Falta Node.js en este computador. Pidale a Claude que lo instale. & pause & exit /b 1)
if not exist node_modules (
  echo Instalando dependencias por primera vez...
  call npm install --no-audit --no-fund
)
node puente.mjs %*
rem Si se apago a proposito (boton Detener) la ventana se cierra sola.
rem Si fallo, avisa y se queda abierta para que se pueda leer el error.
if errorlevel 1 (
  powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('El puente de WhatsApp no pudo arrancar. El detalle esta en la ventana negra de la barra de tareas.', 'WhatsApp IA') | Out-Null"
  pause
)
