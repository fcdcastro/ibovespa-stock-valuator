@echo off
title Servidor Le Gran - Porta 5000
cd /d "%~dp0"
echo ========================================
echo  Servidor de Acoes Le Gran
echo  Iniciando em http://localhost:5000
echo ========================================
echo.
python server.py
echo.
echo Servidor encerrado.
pause
