# Renova Parse CRM

Unified CRM-like application for real estate data parsing and analytics. Combines Zillow property parsing, Seattle Building Permits, and MyBuildingPermit (King County) into a single professional interface.

## Features

- **Zillow Parser** — Extract property listings from Zillow search URLs  
  QuadTree-based tile system, deduplication, export to CSV/Excel.

- **Permit Parser** — Seattle Building Permits  
  Socrata SODA API, Owner-Builder verification via Accela Portal, filtering by class, cost, year.

- **MyBuildingPermit Parser** — King County area (15 jurisdictions)  
  Playwright browser automation, automatic Owner-Builder identification, export to CSV.

- **Analytics Dashboard** — Price/cost charts, timelines, maps, KPI statistics.
- **Data Management** — Unified SQLite database, filtering, export.

## Tech Stack

| Layer   | Stack |
|--------|--------|
| Backend | Python 3.9+, FastAPI, SQLite, Playwright |
| Frontend | Vue 3, Vite, Tailwind CSS, Chart.js, Leaflet.js |

---

## Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 18+** and npm

#### macOS (MacBook)

Install if needed:

```bash
# Homebrew (if not installed): https://brew.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3
brew install python@3.11

# Node.js 18+
brew install node@20
```

Use `python3` and `npm` in the commands below.

#### Windows

Use `python` and `npm`. Optionally double-click `start.bat` to launch.

### One-command launch

```bash
python start.py
```

Or: `npm start`  
On macOS/Linux you can also use: `chmod +x start.sh && ./start.sh`

The script will:

1. Check Python and Node.js
2. Install dependencies (pip + npm) if missing
3. Install Playwright (Chromium) for Owner-Builder verification
4. Start backend (port 8000) and frontend (port 5173)

### Stopping and restarting

1. **Stop everything:** press **Ctrl+C** in the terminal where `start.py` is running (on Mac use **Ctrl+C** in Terminal, not Cmd).
2. **Kill all terminals:** in Cursor/VS Code — right-click terminal panel → "Kill All Terminals".
3. **Start again:** open a new terminal and run `python start.py` (or `python3 start.py` on Mac).

---

## Running on macOS (for the customer)

1. **Clone the repository** (or download and unzip):

   ```bash
   git clone <repository-url> renova-parse-app
   cd renova-parse-app
   ```

2. **Install prerequisites** (see above) if Python 3.9+ or Node 18+ are not installed.

3. **Start the app:**

   ```bash
   python3 start.py
   ```

   Wait until you see:
   - `Backend API:  http://localhost:8000`
   - `Frontend:     http://localhost:5173`

4. **Open in browser:**  
   Go to **http://localhost:5173**

5. **Stop:** Press **Ctrl+C** in the same terminal.

---

## Project structure

```
renova-parse-app/
├── backend/                    # FastAPI backend
│   ├── routers/                # API endpoints (zillow, permits, mybuildingpermit, analytics)
│   ├── services/               # Business logic (parsers)
│   ├── data/                   # SQLite database (created at runtime)
│   ├── database.py, models.py, main.py
│   └── requirements.txt
├── frontend/                    # Vue 3 + Vite
│   ├── src/views/              # Dashboard, ZillowParse, PermitParse, MyBuildingPermit, Analytics, AllData
│   ├── src/api.js              # API client
│   └── package.json
├── parsers/                     # Parser engines / reference
│   ├── zillow-parsing/
│   ├── mybuildingpermit-parsing/
│   └── permit-parsing/
├── start.py                     # Unified launcher (all platforms)
├── start.sh                     # macOS/Linux launcher
├── start.bat                    # Windows launcher
├── package.json                 # npm start → python start.py
├── README.md
└── RELOAD_STEPS.md              # Troubleshooting and full reload
```

---

## Main commands

| Command | Description |
|--------|-------------|
| `python start.py` | Start backend + frontend (installs deps if needed) |
| `python start.py --backend` | Backend only |
| `python start.py --frontend` | Frontend only |
| `python start.py --skip-install` | Start without installing dependencies |
| `npm start` | Same as `python start.py` |

### Manual start (separate terminals)

```bash
# Backend
cd backend
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload

# Frontend (other terminal)
cd frontend
npm install
npm run dev
```

---

## URLs

| Service     | URL |
|------------|-----|
| Frontend   | http://localhost:5173 |
| Backend API| http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ReDoc      | http://localhost:8000/redoc |

---

## Usage

1. **Dashboard** — Overview, quick actions.
2. **Zillow Parsing** — Paste Zillow search URL, run parsing.
3. **Permits Parsing** — Seattle permits: year, class, cost, Owner-Builder verification.
4. **MyBuildingPermit** — King County permits: select cities, Owner-Builder detection.
5. **Analytics** — Charts, maps, KPI.
6. **All Data** — View, filter, export CSV/Excel.

**Browser visible:** In Permit Parse and MyBuildingPermit forms, the "Browser visible" toggle shows the browser window during verification when enabled; when off, the browser runs in the background (headless).  
**Cancel a running job:** Use the **Cancel** button on the job card; closing the terminal does not stop the backend.

---

## Publishing to GitHub

- Ensure `.gitignore` is present (database files, `node_modules`, `.env`, `venv` are ignored).
- Do not commit `backend/data/*.db` or secrets.
- After push, the customer can clone and follow "Running on macOS" above.

---

## Troubleshooting

See **RELOAD_STEPS.md** for full reload, Playwright setup, and cache clearing.

---

## License

MIT
