# Zillow Parsing

Парсинг Zillow по готовым URL с фильтрами. Настраиваешь фильтры в браузере, копируешь URL — скрипт парсит.

## Быстрый старт

Одна команда — проверка зависимостей, установка при необходимости и запуск:

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh && ./start.sh

# Или через Python
python start.py
```

Открой http://localhost:5173 в браузере.

Скрипт автоматически:
- Проверяет Python и npm
- Устанавливает backend зависимости (fastapi, uvicorn)
- Устанавливает frontend зависимости (npm install)
- Запускает backend (порт 8000) и frontend (порт 5173)

## Веб-интерфейс

- Вставка нескольких URL (по одному на строку)
- Статус парсинга в реальном времени
- История парсингов
- Экспорт в CSV
- SQLite для хранения результатов

## CLI скрипты

| Скрипт | Описание |
|--------|----------|
| `scripts/parsers/parse_from_url.py` | Универсальный — любой URL |
| `scripts/parsers/parse_seattle_urls.py` | Seattle по 4 готовым URL |

```bash
pip install playwright playwright-stealth
playwright install firefox

python scripts/parsers/parse_from_url.py
python scripts/parsers/parse_seattle_urls.py
```

## Как это работает

1. Открой Zillow в браузере
2. Настрой фильтры (Sold, Price, Basement, Home Type, Sold in last 36m)
3. Настрой область на карте
4. Скопируй URL из адресной строки
5. Вставь URL в веб-интерфейс или CLI
6. Пройди капчу вручную (если появится)
7. Парсинг начнётся автоматически

При ≥500 результатах используется QuadTree разбиение и checkpoint.

## Документация

- [QUICKSTART.md](QUICKSTART.md) — быстрый старт веб-интерфейса
- [README_STRUCTURE.md](README_STRUCTURE.md) — структура проекта
- [docs/SETUP.md](docs/SETUP.md) — установка, stealth, смена IP
- [docs/USAGE.md](docs/USAGE.md) — использование CLI скриптов
- [backend/README.md](backend/README.md) — Backend API
- [frontend/README.md](frontend/README.md) — Frontend UI
