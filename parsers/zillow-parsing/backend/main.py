"""FastAPI application for Zillow parsing web UI"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import csv
import io
import json
from typing import List
from datetime import datetime

from backend.database import init_database, get_connection, dict_factory
from backend.models import ParseRequest, ParseJobStatus, Home, JobListItem
from backend.parser_service import start_parse_job

app = FastAPI(title="Zillow Parser API")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация БД при старте
@app.on_event("startup")
async def startup_event():
    init_database()


@app.get("/")
async def root():
    return {"message": "Zillow Parser API"}


@app.post("/api/parse", response_model=dict)
async def start_parse(request: ParseRequest):
    """Запуск парсинга по списку URL"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="URLs не могут быть пустыми")
    
    # Валидация URL
    valid_urls = []
    for url in request.urls:
        url = url.strip()
        if url and "zillow.com" in url:
            valid_urls.append(url)
    
    if not valid_urls:
        raise HTTPException(status_code=400, detail="Нет валидных URL Zillow")
    
    # Создаём запись в БД
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO parse_jobs (urls, total_urls, status)
        VALUES (?, ?, ?)
    """, (json.dumps(valid_urls), len(valid_urls), "pending"))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Запускаем парсинг в фоне
    start_parse_job(job_id, valid_urls)
    
    return {"job_id": job_id, "status": "started", "total_urls": len(valid_urls)}


@app.get("/api/status/{job_id}", response_model=ParseJobStatus)
async def get_status(job_id: int):
    """Получить статус парсинга"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM parse_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job не найден")
    
    return ParseJobStatus(**job)


@app.get("/api/jobs", response_model=List[JobListItem])
async def get_jobs():
    """Список всех парсингов (история)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, status, total_urls, homes_found, unique_homes, started_at, completed_at
        FROM parse_jobs
        ORDER BY started_at DESC
        LIMIT 100
    """)
    jobs = cursor.fetchall()
    conn.close()
    
    return [JobListItem(**job) for job in jobs]


@app.get("/api/homes", response_model=dict)
async def get_all_homes(
    job_id: int = None,
    date_from: str = None,
    date_to: str = None,
    city: str = None,
    min_price: float = None,
    max_price: float = None,
    search: str = None,
    skip: int = 0,
    limit: int = 500
):
    """Все дома с фильтрами"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if job_id:
        conditions.append("h.job_id = ?")
        params.append(job_id)
    if date_from:
        conditions.append("date(h.created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        conditions.append("date(h.created_at) <= date(?)")
        params.append(date_to)
    if city:
        conditions.append("LOWER(h.city) LIKE ?")
        params.append(f"%{city.lower()}%")
    if min_price is not None:
        conditions.append("h.price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("h.price <= ?")
        params.append(max_price)
    if search:
        conditions.append("(h.address LIKE ? OR h.zipcode LIKE ? OR h.zpid LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT h.id, h.job_id, h.zpid, h.address, h.city, h.state, h.zipcode, 
               h.price, h.beds, h.baths, h.area_sqft, h.created_at
        FROM homes h
        WHERE {where}
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, skip])
    homes = cursor.fetchall()
    
    cursor.execute(f"SELECT COUNT(*) FROM homes h WHERE {where}", params)
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {"homes": [Home(**h) for h in homes], "total": total}


@app.get("/api/homes/stats")
async def get_homes_stats(
    job_id: int = None,
    date_from: str = None,
    date_to: str = None
):
    """Статистика по домам"""
    conn = get_connection()
    cursor = conn.cursor()
    
    conditions = []
    params = []
    if job_id:
        conditions.append("job_id = ?")
        params.append(job_id)
    if date_from:
        conditions.append("date(created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        conditions.append("date(created_at) <= date(?)")
        params.append(date_to)
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT zpid) as unique_count,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(beds) as avg_beds,
            AVG(baths) as avg_baths,
            AVG(area_sqft) as avg_area
        FROM homes
        WHERE {where} AND price IS NOT NULL
    """, params)
    row = cursor.fetchone()
    conn.close()
    
    return {
        "total": row[0],
        "unique_count": row[1],
        "avg_price": round(row[2], 2) if row[2] else 0,
        "min_price": row[3],
        "max_price": row[4],
        "avg_beds": round(row[5], 1) if row[5] else 0,
        "avg_baths": round(row[6], 1) if row[6] else 0,
        "avg_area_sqft": round(row[7], 0) if row[7] else 0,
    }


@app.get("/api/jobs/{job_id}/homes", response_model=List[Home])
async def get_homes(job_id: int, skip: int = 0, limit: int = 100):
    """Получить дома по job_id с пагинацией"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, job_id, zpid, address, city, state, zipcode, price, beds, baths, area_sqft, created_at
        FROM homes
        WHERE job_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (job_id, limit, skip))
    homes = cursor.fetchall()
    conn.close()
    
    return [Home(**home) for home in homes]


@app.get("/api/jobs/{job_id}/export")
async def export_job(job_id: int, format: str = "csv"):
    """Экспорт результатов в CSV или JSON"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT zpid, address, city, state, zipcode, price, beds, baths, area_sqft, created_at
        FROM homes
        WHERE job_id = ?
        ORDER BY created_at DESC
    """, (job_id,))
    homes = cursor.fetchall()
    conn.close()
    
    if not homes:
        raise HTTPException(status_code=404, detail="Дома не найдены")
    
    if format == "csv":
        output = io.StringIO()
        if homes:
            writer = csv.DictWriter(output, fieldnames=homes[0].keys())
            writer.writeheader()
            writer.writerows(homes)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=job_{job_id}_homes.csv"}
        )
    else:
        return {"homes": homes}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
