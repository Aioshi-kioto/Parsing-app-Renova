"""
Zillow API Router
Endpoints для парсинга и получения данных Zillow
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from typing import List, Optional
import csv
import io
import json
import re
from datetime import datetime

from utils.excel_export import create_formatted_excel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_connection, dict_factory, create_zillow_job, update_zillow_job
from models import (
    ZillowParseRequest, ZillowJobStatus, ZillowJobListItem, 
    ZillowHome, ZillowHomesResponse, ZillowStats
)

router = APIRouter()


def _parse_price(value):
    """Преобразует цену из строк вроде '$740,000' или '1.00M' в float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        s = s.replace("$", "").replace(",", "")
        m = re.match(r"^([0-9]*\\.?[0-9]+)m$", s, re.IGNORECASE)
        if m:
            return float(m.group(1)) * 1_000_000
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _dedupe_urls(urls: List[str]) -> List[str]:
    """Удаляет дубликаты URL."""
    seen = set()
    result = []
    for url in urls:
        u = url.strip()
        if not u or "zillow.com" not in u:
            continue
        key = u.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            result.append(u)
    return result


@router.post("/parse", response_model=dict)
async def start_parse(request: ZillowParseRequest):
    """Запуск парсинга Zillow по списку URL"""
    # Валидация и удаление дубликатов URL
    valid_urls = _dedupe_urls(request.urls)
    
    if not valid_urls:
        raise HTTPException(status_code=400, detail="Нет валидных URL Zillow")
    
    # Создаём задачу в БД
    job_id = create_zillow_job(valid_urls)
    
    # Импортируем и запускаем парсер
    from services.parsers.zillow_parser import start_zillow_parse_job
    start_zillow_parse_job(job_id, valid_urls, headless=request.headless)
    
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
               h.price, h.price_formatted, h.beds, h.baths, h.area_sqft, h.lot_size, h.year_built,
               h.home_type, h.date_sold, h.latitude, h.longitude, h.zestimate, h.tax_assessed_value,
               h.has_image, h.detail_url, h.sold_date_text, h.created_at
        FROM zillow_homes h
        WHERE {where}
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, skip])
    homes = cursor.fetchall()
    
    cursor.execute(f"SELECT COUNT(*) FROM zillow_homes h WHERE {where}", params)
    total = cursor.fetchone()["COUNT(*)"]
    
    # Нормализуем price -> float, has_image -> bool
    normalized_homes = []
    for h in homes:
        h = dict(h)
        h["price"] = _parse_price(h.get("price"))
        if h.get("has_image") is not None:
            h["has_image"] = bool(h["has_image"])
        normalized_homes.append(h)
    
    conn.close()
    
    return ZillowHomesResponse(homes=[ZillowHome(**h) for h in normalized_homes], total=total)


@router.get("/stats", response_model=ZillowStats)
async def get_stats(
    job_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Статистика по домам"""
    conn = get_connection()
    conn.row_factory = dict_factory
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
    
    # Счётчики (кроме цен) можно взять агрегатами
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT zpid) as unique_count,
            AVG(beds) as avg_beds,
            AVG(baths) as avg_baths,
            AVG(area_sqft) as avg_area
        FROM zillow_homes
        WHERE {where}
    """, params)
    row = cursor.fetchone()
    
    # Цены — приводим к float в Python, чтобы не падать на строках "$740,000" или "1.00M"
    cursor.execute(f"SELECT price FROM zillow_homes WHERE {where}", params)
    price_rows = cursor.fetchall()
    prices = []
    for pr_row in price_rows:
        # С dict_factory это словарь, иначе кортеж
        raw_price = pr_row.get("price") if isinstance(pr_row, dict) else (pr_row[0] if isinstance(pr_row, tuple) else pr_row)
        val = _parse_price(raw_price)
        if val is not None:
            prices.append(val)
    
    conn.close()
    
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0
    min_price = min(prices) if prices else None
    max_price = max(prices) if prices else None
    
    # С dict_factory row - это словарь
    row_dict = row if isinstance(row, dict) else {
        "total": row[0] if len(row) > 0 else 0,
        "unique_count": row[1] if len(row) > 1 else 0,
        "avg_beds": row[2] if len(row) > 2 else 0,
        "avg_baths": row[3] if len(row) > 3 else 0,
        "avg_area": row[4] if len(row) > 4 else 0,
    }
    
    return ZillowStats(
        total=row_dict.get("total") or 0,
        unique_count=row_dict.get("unique_count") or 0,
        avg_price=avg_price,
        min_price=min_price,
        max_price=max_price,
        avg_beds=round(row_dict.get("avg_beds") or 0, 1),
        avg_baths=round(row_dict.get("avg_baths") or 0, 1),
        avg_area_sqft=round(row_dict.get("avg_area") or 0, 0),
    )


@router.get("/export/{job_id}")
async def export_job(job_id: int, format: str = Query(default="csv", enum=["csv", "json", "xlsx"])):
    """Экспорт результатов в CSV, JSON или Excel"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT zpid, address, city, state, zipcode, price, price_formatted, beds, baths, 
               area_sqft, lot_size, year_built, home_type, date_sold, latitude, longitude,
               zestimate, tax_assessed_value, has_image, detail_url, sold_date_text, created_at
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
    elif format == "xlsx":
        excel_bytes = create_formatted_excel(
            homes,
            sheet_name="Zillow Homes",
            currency_columns=["price", "zestimate", "tax_assessed_value"],
            header_bg="2563EB",
        )
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=zillow_job_{job_id}.xlsx"}
        )
    else:
        return {"homes": homes}


@router.get("/export")
async def export_all(
    format: str = Query(default="csv", enum=["csv", "json", "xlsx"]),
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_beds: Optional[int] = None,
    max_beds: Optional[int] = None,
    search: Optional[str] = None,
):
    """Экспорт всех домов с фильтрами (CSV, JSON, Excel)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if city:
        conditions.append("LOWER(city) LIKE ?")
        params.append(f"%{city.lower()}%")
    if state:
        conditions.append("LOWER(state) = ?")
        params.append(state.lower())
    if min_price is not None:
        conditions.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)
    if min_beds is not None:
        conditions.append("beds >= ?")
        params.append(min_beds)
    if max_beds is not None:
        conditions.append("beds <= ?")
        params.append(max_beds)
    if search:
        conditions.append("(address LIKE ? OR zipcode LIKE ? OR zpid LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT zpid, address, city, state, zipcode, price, price_formatted, beds, baths, 
               area_sqft, lot_size, year_built, home_type, date_sold, latitude, longitude,
               zestimate, tax_assessed_value, has_image, detail_url, sold_date_text, created_at
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
    elif format == "xlsx":
        excel_bytes = create_formatted_excel(
            homes,
            sheet_name="Zillow Homes",
            currency_columns=["price", "zestimate", "tax_assessed_value"],
            header_bg="2563EB",
        )
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=zillow_export_{timestamp}.xlsx"}
        )
    else:
        return {"homes": homes, "total": len(homes)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_zillow_job(job_id: int):
    """Остановить задачу парсинга Zillow"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, status FROM zillow_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] not in ("running", "pending", "parsing", "waiting_captcha"):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job['status']}'")
    
    cursor.execute("""
        UPDATE zillow_jobs SET status = 'cancelled', completed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()
    
    return {"status": "cancelled", "job_id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_zillow_job(job_id: int):
    """Удалить задачу и связанные дома"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM zillow_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    cursor.execute("DELETE FROM zillow_homes WHERE job_id = ?", (job_id,))
    homes_deleted = cursor.rowcount
    cursor.execute("DELETE FROM zillow_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    
    return {"status": "deleted", "job_id": job_id, "homes_deleted": homes_deleted}
