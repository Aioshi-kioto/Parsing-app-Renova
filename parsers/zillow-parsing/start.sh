#!/bin/bash

echo "========================================"
echo "Запуск Zillow Parser Web UI"
echo "========================================"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "[ОШИБКА] Python3 не найден!"
    echo "Установите Python с https://www.python.org/"
    exit 1
fi

# Проверка npm
if ! command -v npm &> /dev/null; then
    echo "[ОШИБКА] npm не найден!"
    echo "Установите Node.js с https://nodejs.org/"
    exit 1
fi

echo "Python и npm найдены, запускаю скрипт..."
echo ""

# Запуск через Python скрипт
python3 start.py
