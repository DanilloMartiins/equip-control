@echo off
cd /d "%~dp0"
echo ========================================
echo  AXIA - Sistema de Controle de Equipamentos
echo ========================================
echo.
echo Iniciando servidor...
echo Acesse: http://127.0.0.1:5000
echo.
python app.py
pause
