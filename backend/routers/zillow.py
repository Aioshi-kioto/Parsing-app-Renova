"""
Zillow API Router
Endpoints для парсинга и получения данных Zillow
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import csv
import io
import json
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_connection, dict_factory, create_zillow_job, update_zillow_job
from models import (
    ZillowParseRequest, ZillowJobStatus, ZillowJobListItem, 
    ZillowHome, ZillowHomesResponse, ZillowStats
)

router = APIRouter()


@router.post("/parse", response_model=dict)
async def start_parse(request: ZillowParseRequest):
    """Запуск парсинга Zillow по списку URL"""
    # Валидация URL
    valid_urls = []
    for url in request.urls:
        url = url.strip()
        if url and "zillow.com" in url:
            valid_urls.append(url)
    
    if not valid_urls:
        raise HTTPException(status_code=400, detail="Нет валидных URL Zillow")
    
    # Создаём задачу в БД
    job_id = create_zillow_job(valid_urls)
    
    # Импортируем и запускаем парсер
    from services.zillow_parser import start_zillow_parse_job
    start_zillow_parse_job(job_id, valid_urls)
    
    return {"job_id": job_id, "status": "started", "total_urls": len(valid_urls)}


@router.get("/status/{job_id}", response_model=ZillowJobStatus)
async def get_status(job_id: int):
    """Получить статус парсинга"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM zillow_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job не найден")
    
    return ZillowJobStatus(**job)


@router.get("/jobs", response_model=List[ZillowJobListItem])
async def get_jobs(limit: int = 100):
    """Список всех парсингов (история)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, status, total_urls, homes_found, unique_homes, started_at, completed_at
        FROM zillow_jobs
        ORDER BY started_at DESC
        LIMIT ?
    """, (limit,))
    jobs = cursor.fetchall()
    conn.close()
    
    return [ZillowJobListItem(**job) for job in jobs]


@router.get("/homes", response_model=ZillowHomesResponse)
async def get_homes(
    job_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_beds: Optional[int] = None,
    max_beds: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000)
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
    if state:
        conditions.append("LOWER(h.state) = ?")
        params.append(state.lower())
    if min_price is not None:
        conditions.append("h.price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("h.price <= ?")
        params.append(max_price)
    if min_beds is not None:
        conditions.append("h.beds >= ?")
        params.append(min_beds)
    if max_beds is not None:
        conditions.append("h.beds <= ?")
        params.append(max_beds)
    if search:
        conditions.append("(h.address LIKE ? OR h.zipcode LIKE ? OR h.zpid LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT h.id, h.job_id, h.zpid, h.address, h.city, h.state, h.zipcode, 
               h.price, h.beds, h.baths, h.area_sqft, h.lot_size, h.year_built,
               h.home_type, h.latitude, h.longitude, h.created_at
        FROM zillow_homes h
        WHERE {where}
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, skip])
    homes = cursor.fetchall()
    
    cursor.execute(f"SELECT COUNT(*) FROM zillow_homes h WHERE {where}", params)
    total = cursor.fetchone()["COUNT(*)"]
    
    conn.close()
    
    return ZillowHomesResponse(homes=[ZillowHome(**h) for h in homes], total=total)


@router.get("/stats", response_model=ZillowStats)
async def get_stats(
    job_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
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
        FROM zillow_homes
        WHERE {where} AND price IS NOT NULL
    """, params)
    row = cursor.fetchone()
    conn.close()
    
    return ZillowStats(
        total=row[0] or 0,
        unique_count=row[1] or 0,
        avg_price=round(row[2], 2) if row[2] else 0,
        min_price=row[3],
        max_price=row[4],
        avg_beds=round(row[5], 1) if row[5] else 0,
        avg_baths=round(row[6], 1) if row[6] else 0,
        avg_area_sqft=round(row[7], 0) if row[7] else 0,
    )


@router.get("/export/{job_id}")
async def export_job(job_id: int, format: str = Query(default="csv", enum=["csv", "json"])):
    """Экспорт результатов в CSV или JSON"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT zpid, address, city, state, zipcode, price, beds, baths, 
               area_sqft, lot_size, year_built, home_type, latitude, longitude, created_at
        FROM zillow_homes
        WHERE job_id = ?
        ORDER BY created_at DESC
    """, (job_id,))
    homes = cursor.fetchall()
    conn.close()
    
    if not homes:
        raise HTTPException(status_code=404, detail="Дома не найдены")
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=homes[0].keys())
        writer.writeheader()
        writer.writerows(homes)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=zillow_job_{job_id}.csv"}
        )
    else:
        return {"homes": homes}


@router.get("/export")
async def export_all(
    format: str = Query(default="csv", enum=["csv", "json"]),
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """Экспорт всех домов с фильтрами"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if city:
        conditions.append("LOWER(city) LIKE ?")
        params.append(f"%{city.lower()}%")
    if min_price is not None:
        conditions.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT zpid, address, city, state, zipcode, price, beds, baths, 
               area_sqft, lot_size, year_built, home_type, latitude, longitude, created_at
        FROM zillow_homes
        WHERE {where}
        ORDER BY created_at DESC
    """, params)
    homes = cursor.fetchall()
    conn.close()
    
    if not homes:
        raise HTTPException(status_code=404, detail="Дома не найдены")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=homes[0].keys())
        writer.writeheader()
        writer.writerows(homes)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=zillow_export_{timestamp}.csv"}
        )
    else:
        return {"homes": homes, "total": len(homes)}
