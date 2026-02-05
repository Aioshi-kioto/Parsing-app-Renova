# Backend - Zillow Parser API

FastAPI backend для веб-интерфейса парсинга Zillow.

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен на http://localhost:8000

Документация API: http://localhost:8000/docs

## Структура

- `main.py` - FastAPI приложение, endpoints
- `database.py` - SQLite инициализация и схемы
- `models.py` - Pydantic модели
- `parser_service.py` - Логика парсинга, интеграция с core
- `data/zillow.db` - SQLite база данных (создаётся автоматически)
