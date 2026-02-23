# MyBuildingPermit Integration Summary

## Обзор

Парсер MyBuildingPermit полностью интегрирован в главное приложение Renova Parse CRM. Запускается одной командой вместе со всеми другими парсерами.

---

## Запуск

```bash
# Из корня проекта
python start.py
```

Или: `npm start` / `start.bat`

После запуска:

- **Frontend**: <http://localhost:5173/mybuildingpermit>
- **API Docs**: <http://localhost:8000/docs>

---

## Интеграция с Backend

| Файл | Описание |
|------|----------|
| `backend/routers/mybuildingpermit.py` | API endpoints `/api/mybuildingpermit/*` |
| `backend/services/mybuildingpermit_parser.py` | Playwright скрапер |
| `backend/database.py` | Таблицы `mbp_jobs`, `mbp_permits` |
| `backend/models.py` | Pydantic модели `MBPParseRequest`, `MBPPermit` |

---

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/mybuildingpermit/jurisdictions` | Список 15 городов |
| POST | `/api/mybuildingpermit/parse` | Запуск парсинга |
| GET | `/api/mybuildingpermit/status/{job_id}` | Статус задачи |
| GET | `/api/mybuildingpermit/jobs` | История парсингов |
| GET | `/api/mybuildingpermit/list` | Список пермитов |
| GET | `/api/mybuildingpermit/owner-builders` | Только Owner-Builders |
| GET | `/api/mybuildingpermit/export` | Экспорт CSV |

---

## Юрисдикции (15 городов)

Auburn, Bellevue, Bothell, Burien, Edmonds, Federal Way, Issaquah, Kenmore, King County, Kirkland, Mercer Island, Mill Creek, Newcastle, Sammamish, Snoqualmie

---

## Использование UI

1. Открыть **MyBuildingPermit** в меню слева
2. Выбрать города (чекбоксы)
3. Настроить **Days Back** (период) и **Limit Per City**
4. Нажать **Start Parse**
5. Следить за статусом в реальном времени
6. Скачать CSV после завершения

---

## Standalone Mode (только этот парсер)

Если нужен только CLI без UI:

```bash
cd parsers/mybuildingpermit-parsing
pip install -r requirements.txt
playwright install chromium
python src/scraper.py --test-mode
```

---

## Файлы в этой папке

| Файл | Описание |
|------|----------|
| `config.py` | Конфигурация: юрисдикции, селекторы, настройки браузера |
| `src/scraper.py` | Основной Playwright скрапер |
| `src/export.py` | Экспорт в Excel (standalone) |
| `requirements.txt` | Зависимости Python |
| `docs/` | HTML-примеры страниц сайта |

---

## Зависимости

```
playwright>=1.40.0
playwright-stealth>=1.0.6
beautifulsoup4>=4.12.0
lxml>=5.0.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
loguru>=0.7.0
```
