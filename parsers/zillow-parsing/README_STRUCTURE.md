# Структура проекта

```
zillow-parsing/
├── start.py              # Запуск backend + frontend одной командой
├── start.bat             # Запуск (Windows)
├── start.sh              # Запуск (Linux/Mac)
├── backend/              # FastAPI backend
│   ├── main.py           # API endpoints
│   ├── database.py       # SQLite
│   ├── models.py         # Pydantic модели
│   ├── parser_service.py # Логика парсинга
│   ├── requirements.txt
│   └── data/             # zillow.db (создаётся автоматически)
├── frontend/             # Vue 3 + Vite + Tailwind
│   ├── src/
│   │   ├── App.vue
│   │   ├── api.js
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── src/core/             # Библиотека парсинга
│   ├── playwright_search.py
│   ├── tiling.py
│   └── ...
├── scripts/parsers/
│   ├── parse_from_url.py      # Универсальный — любой URL
│   └── parse_seattle_urls.py  # Seattle по готовым URL
├── docs/
│   ├── SETUP.md
│   └── USAGE.md
├── config/
├── logs/
├── pyproject.toml
├── README.md
├── QUICKSTART.md
└── README_STRUCTURE.md
```

## Порты

| Сервис | Порт | URL |
|--------|------|-----|
| Frontend | 5173 | http://localhost:5173 |
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |

## Импорты (скрипты и backend)

Скрипты добавляют `src/` в `sys.path`:

```python
from core.playwright_search import search_from_url_playwright_sync
from core.tiling import remove_duplicates
```
