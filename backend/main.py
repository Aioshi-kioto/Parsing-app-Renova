"""
Renova Parse CRM - Main FastAPI Application
Единый backend для парсинга Zillow и Seattle Building Permits
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_database
from routers import zillow, permits, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте приложения"""
    init_database()
    print("[OK] Database initialized")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Renova Parse CRM",
    description="CRM система для парсинга недвижимости Zillow и строительных пермитов Seattle",
    version="1.0.0",
    lifespan=lifespan
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

# Подключаем роутеры
app.include_router(zillow.router, prefix="/api/zillow", tags=["Zillow"])
app.include_router(permits.router, prefix="/api/permits", tags=["Permits"])
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
            "analytics": "/api/analytics",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
