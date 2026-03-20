"""
Renova Parse CRM - Main FastAPI Application
Единый backend для парсинга Zillow и Seattle Building Permits
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import time

try:
    from backend.database import init_database, get_connection
    from backend.routers import zillow, permits, analytics, mybuildingpermit, tasks, telegram
    from backend.routers import leads, dashboard, jobs, simulation, outbound, parser_settings, scheduled_operations, provider_costs
except ImportError:
    from database import init_database, get_connection
    from routers import zillow, permits, analytics, mybuildingpermit, tasks, telegram
    from routers import leads, dashboard, jobs, simulation, outbound, parser_settings, scheduled_operations, provider_costs


def _check_playwright():
    """Проверка Playwright для верификации owner-builder."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        print("[OK] Playwright ready (Owner-Builder verification enabled)")
        return True
    except ImportError:
        print("[WARN] Playwright not installed. Owner-Builder verification will be disabled.")
        print("       Fix: pip install playwright playwright-stealth && playwright install chromium")
        return False
    except Exception as e:
        print(f"[WARN] Playwright browsers missing or error: {e}")
        print("       Fix: playwright install chromium")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте приложения"""
    skip_db = os.getenv("SKIP_DB_INIT", "").strip().lower() in ("1", "true", "yes", "y")
    if skip_db:
        print("[WARN] SKIP_DB_INIT=1 — skipping database initialization.")
    else:
        try:
            init_database()
            print("[OK] PostgreSQL database initialized")
        except Exception as e:
            print(f"[WARN] Database init failed, continuing without DB. Error: {e}")
    try:
        await telegram.setup_telegram_bot_commands()
    except Exception as e:
        print(f"[WARN] Telegram command menu setup failed: {e}")
    _check_playwright()
    yield
    print("Shutting down...")


app = FastAPI(
    title="Renova Parse CRM",
    description="CRM система для парсинга недвижимости Zillow и строительных пермитов Seattle",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,   # отключено: API docs не используются
    redoc_url=None,
    openapi_url=None,
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",  # Vite fallback when 5173 busy
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов"""
    start_time = time.time()
    print(f"\n[API REQUEST] {request.method} {request.url.path}")
    if request.url.query:
        print(f"[API REQUEST] Query params: {request.url.query}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        print(f"[API REQUEST] {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        # ASCII-only: Windows console may be cp1251
        print(f"[API REQUEST] ERROR {request.method} {request.url.path} - {e} - Time: {process_time:.3f}s")
        raise

# Подключаем роутеры
app.include_router(zillow.router, prefix="/api/zillow", tags=["Zillow"])
app.include_router(permits.router, prefix="/api/permits", tags=["Permits"])
app.include_router(mybuildingpermit.router, prefix="/api/mybuildingpermit", tags=["MyBuildingPermit"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
app.include_router(outbound.router, prefix="/api/outbound", tags=["Outbound"])
app.include_router(parser_settings.router, prefix="/api/parser-settings", tags=["ParserSettings"])
app.include_router(scheduled_operations.router, prefix="/api/scheduled-operations", tags=["ScheduledOperations"])
app.include_router(provider_costs.router, prefix="/api/provider-costs", tags=["ProviderCosts"])


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "name": "Renova Parse CRM",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "zillow": "/api/zillow",
            "permits": "/api/permits",
            "mybuildingpermit": "/api/mybuildingpermit",
            "analytics": "/api/analytics",
            "leads": "/api/leads",
            "tasks": "/api/tasks",
            "telegram": "/api/telegram",
        }
    }


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса и доступности PostgreSQL."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        db_ok = bool(row and row[0] == 1)
        if not db_ok:
            raise HTTPException(status_code=503, detail={"status": "unhealthy", "db": "down"})
        return {"status": "healthy", "db": "up"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "db": "down", "error": str(e)},
        )
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
