@echo off
echo ========================================
echo Запуск Zillow Parser Web UI
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с https://www.python.org/
    pause
    exit /b 1
)

REM Проверка npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] npm не найден!
    echo Установите Node.js с https://nodejs.org/
    pause
    exit /b 1
)

echo Python и npm найдены, запускаю скрипт...
echo.

REM Запуск через Python скрипт
python start.py

pause
