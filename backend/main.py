"""
Renova Parse CRM - Main FastAPI Application
Единый backend для парсинга Zillow и Seattle Building Permits
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time

from database import init_database
from routers import zillow, permits, analytics, mybuildingpermit


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
    init_database()
    print("[OK] Database initialized")
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
        }
    }


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
