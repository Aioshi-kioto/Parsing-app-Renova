# Renova Parse CRM

Unified CRM-like application for real estate data parsing and analytics. Combines Zillow property parsing and Seattle Building Permits data into a single professional interface.

## Features

- **Zillow Parser** — Extract property listings from Zillow search URLs
  - QuadTree-based tile system for comprehensive coverage
  - Deduplication and data normalization
  - Export to CSV/Excel

- **Permit Parser** — Seattle Building Permits data
  - Integration with Socrata SODA API
  - Owner-Builder verification via Accela Portal
  - Filtering by class, cost, year

- **Analytics Dashboard** — Price/cost charts, timelines, maps, KPI statistics
- **Data Management** — Unified SQLite database, filtering, export

## Tech Stack

| Layer    | Stack                          |
|----------|--------------------------------|
| Backend  | Python 3.9+, FastAPI, SQLite, Playwright |
| Frontend | Vue 3, Vite, Tailwind CSS, Chart.js, Leaflet.js |

---

## Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 18+** and npm

### One Command Launch

```bash
python start.py
```

Или: `npm start` / двойной клик по `start.bat` (Windows).

**Скрипт автоматически:**
1. Проверяет Python и Node.js
2. Устанавливает зависимости (pip + npm), если их нет
3. Устанавливает Playwright (Chromium)
4. Запускает backend (порт 8000) и frontend (порт 5173)

### Остановка и перезапуск

1. **Остановить все:** нажмите `Ctrl+C` в терминале, где запущен `start.py`
2. **Закрыть все терминалы:** в Cursor/VS Code — правый клик по панели терминалов → "Kill All Terminals"
3. **Запуск с нуля:** откройте новый терминал и выполните `python start.py`

---

## Project Structure

```
renova-parse-app/
├── backend/                    # FastAPI backend
│   ├── routers/                # API endpoints
│   │   ├── zillow.py           # Zillow parse, status, export
│   │   ├── permits.py          # Permits parse, status, export
│   │   └── analytics.py        # Charts, maps, stats
│   ├── services/               # Business logic
│   │   ├── zillow_parser.py    # Zillow parsing (uses parsers/)
│   │   └── permit_parser.py   # Seattle permits (Socrata + Accela)
│   ├── data/                   # SQLite database
│   ├── database.py
│   ├── models.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/                   # Vue 3 + Vite
│   ├── src/
│   │   ├── views/              # Dashboard, ZillowParse, PermitParse, Analytics, AllData
│   │   ├── layouts/            # MainLayout (sidebar)
│   │   ├── router/
│   │   └── api.js              # API client
│   └── package.json
│
├── parsers/                    # Parser engines (used by backend)
│   ├── zillow-parsing/         # Zillow core (QuadTree, Playwright)
│   └── permit-parsing/         # Permit reference/utilities
│
├── start.py                    # Unified launcher
├── start.bat                   # Windows launcher
├── package.json                # npm start → python start.py
└── README.md
```

> **Примечание:** Папки `permit parsing/` и `zillow-parsing/` в корне — это старые дубликаты. Используется только `parsers/`. Их можно удалить.

---

## Main Commands

| Команда | Описание |
|---------|----------|
| `python start.py` | Запуск backend + frontend (с проверкой зависимостей) |
| `python start.py --backend` | Только backend |
| `python start.py --frontend` | Только frontend |
| `python start.py --skip-install` | Запуск без установки зависимостей |
| `npm start` | Алиас для `python start.py` |

### Ручной запуск (если нужен раздельный)

```bash
# Backend
cd backend
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload

# Frontend (в другом терминале)
cd frontend
npm install
npm run dev
```

---

## URLs

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Usage

1. **Dashboard** — общая статистика, быстрые действия
2. **Zillow Parsing** — вставьте URL поиска Zillow, запустите парсинг
3. **Permits Parsing** — настройте год, класс, стоимость, верификацию owner-builder
4. **Analytics** — графики, карты, KPI
5. **All Data** — просмотр, фильтры, экспорт CSV

---

## License

MIT
