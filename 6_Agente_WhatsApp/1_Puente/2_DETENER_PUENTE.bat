@echo off
chcp 65001 >nul
rem Apaga el bot de una: cierra el puente. Su WhatsApp sigue normal.
curl -s -m 5 -X POST -H "x-puente: 1" http://localhost:3939/accion/detener >nul 2>&1 && (echo Puente detenido. Nadie le contesta por usted.) || (echo El puente no estaba prendido.)
timeout /t 3 >nul
