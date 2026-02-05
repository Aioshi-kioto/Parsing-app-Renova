"""
Permits API Router
Endpoints для парсинга и получения данных Seattle Building Permits
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

from database import get_connection, dict_factory, create_permit_job, update_permit_job
from models import (
    PermitParseRequest, PermitJobStatus, PermitJobListItem,
    Permit, PermitsResponse, PermitStats
)

router = APIRouter()


@router.post("/parse", response_model=dict)
async def start_parse(request: PermitParseRequest):
    """Запуск парсинга пермитов"""
    job_id = create_permit_job(
        year=request.year,
        permit_class=request.permit_class,
        min_cost=request.min_cost
    )
    
    from services.permit_parser import start_permit_parse_job
    start_permit_parse_job(
        job_id=job_id,
        year=request.year,
        month=request.month,
        period=request.period,
        permit_class=request.permit_class,
        min_cost=request.min_cost,
        verify=request.verify_owner_builder
    )
    
    return {
        "job_id": job_id,
        "status": "started",
        "year": request.year,
        "period": request.period or (f"month-{request.month}" if request.month else "year"),
        "permit_class": request.permit_class
    }


@router.get("/status/{job_id}", response_model=PermitJobStatus)
async def get_status(job_id: int):
    """Получить статус парсинга пермитов"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM permit_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job не найден")
    
    return PermitJobStatus(**job)


@router.get("/jobs", response_model=List[PermitJobListItem])
async def get_jobs(limit: int = 100):
    """Список всех парсингов пермитов (история)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, status, year, permits_found, owner_builders_found, error_message, started_at, completed_at
        FROM permit_jobs
        ORDER BY started_at DESC
        LIMIT ?
    """, (limit,))
    jobs = cursor.fetchall()
    conn.close()
    
    return [PermitJobListItem(**job) for job in jobs]


@router.get("/list", response_model=PermitsResponse)
async def get_permits(
    job_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    city: Optional[str] = None,
    permit_class: Optional[str] = None,
    is_owner_builder: Optional[bool] = None,
    verification_status: Optional[str] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Все пермиты с фильтрами"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if job_id:
        conditions.append("p.job_id = ?")
        params.append(job_id)
    if date_from:
        conditions.append("date(p.applied_date) >= date(?)")
        params.append(date_from)
    if date_to:
        conditions.append("date(p.applied_date) <= date(?)")
        params.append(date_to)
    if city:
        conditions.append("LOWER(p.city) LIKE ?")
        params.append(f"%{city.lower()}%")
    if permit_class:
        conditions.append("LOWER(p.permit_class) LIKE ?")
        params.append(f"%{permit_class.lower()}%")
    if is_owner_builder is not None:
        conditions.append("p.is_owner_builder = ?")
        params.append(1 if is_owner_builder else 0)
    if verification_status:
        conditions.append("p.verification_status = ?")
        params.append(verification_status)
    if min_cost is not None:
        conditions.append("p.est_project_cost >= ?")
        params.append(min_cost)
    if max_cost is not None:
        conditions.append("p.est_project_cost <= ?")
        params.append(max_cost)
    if search:
        conditions.append("""
            (p.permit_num LIKE ? OR p.address LIKE ? OR p.description LIKE ?)
        """)
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT p.id, p.job_id, p.permit_num, p.permit_class, p.permit_class_mapped,
               p.permit_type_mapped, p.permit_type_desc, p.description, p.est_project_cost,
               p.applied_date, p.issued_date, p.status_current, p.address, p.city, 
               p.state, p.zipcode, p.contractor_name, p.is_owner_builder,
               p.verification_status, p.work_performer_text, p.portal_link,
               p.latitude, p.longitude, p.created_at, p.updated_at
        FROM permits p
        WHERE {where}
        ORDER BY p.applied_date DESC, p.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, skip])
    permits = cursor.fetchall()
    
    cursor.execute(f"SELECT COUNT(*) FROM permits p WHERE {where}", params)
    total = cursor.fetchone()["COUNT(*)"]
    
    conn.close()
    
    # Конвертируем is_owner_builder из int в bool
    for p in permits:
        if p.get('is_owner_builder') is not None:
            p['is_owner_builder'] = bool(p['is_owner_builder'])
    
    return PermitsResponse(permits=[Permit(**p) for p in permits], total=total)


@router.get("/stats", response_model=PermitStats)
async def get_stats(
    job_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Статистика по пермитам"""
    conn = get_connection()
    cursor = conn.cursor()
    
    conditions = []
    params = []
    if job_id:
        conditions.append("job_id = ?")
        params.append(job_id)
    if date_from:
        conditions.append("date(applied_date) >= date(?)")
        params.append(date_from)
    if date_to:
        conditions.append("date(applied_date) <= date(?)")
        params.append(date_to)
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_owner_builder = 1 THEN 1 ELSE 0 END) as owner_builders,
            SUM(CASE WHEN is_owner_builder = 0 THEN 1 ELSE 0 END) as contractors,
            SUM(CASE WHEN is_owner_builder IS NULL THEN 1 ELSE 0 END) as unknown,
            AVG(est_project_cost) as avg_cost,
            MIN(est_project_cost) as min_cost,
            MAX(est_project_cost) as max_cost,
            SUM(est_project_cost) as total_cost
        FROM permits
        WHERE {where} AND est_project_cost IS NOT NULL
    """, params)
    row = cursor.fetchone()
    conn.close()
    
    return PermitStats(
        total=row[0] or 0,
        owner_builders=row[1] or 0,
        contractors=row[2] or 0,
        unknown=row[3] or 0,
        avg_cost=round(row[4], 2) if row[4] else 0,
        min_cost=row[5],
        max_cost=row[6],
        total_cost=round(row[7], 2) if row[7] else 0,
    )


@router.get("/owner-builders", response_model=PermitsResponse)
async def get_owner_builders(
    job_id: Optional[int] = None,
    min_cost: Optional[float] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Получить только owner-builders"""
    return await get_permits(
        job_id=job_id,
        is_owner_builder=True,
        min_cost=min_cost,
        skip=skip,
        limit=limit
    )


@router.get("/export/{job_id}")
async def export_job(
    job_id: int, 
    format: str = Query(default="csv", enum=["csv", "json"]),
    only_owners: bool = Query(default=False)
):
    """Экспорт результатов в CSV или JSON"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    owner_filter = "AND is_owner_builder = 1" if only_owners else ""
    
    cursor.execute(f"""
        SELECT permit_num, permit_class, permit_type_mapped, description,
               est_project_cost, applied_date, address, city, state, zipcode,
               contractor_name, is_owner_builder, verification_status, 
               work_performer_text, portal_link, created_at
        FROM permits
        WHERE job_id = ? {owner_filter}
        ORDER BY applied_date DESC
    """, (job_id,))
    permits = cursor.fetchall()
    conn.close()
    
    if not permits:
        raise HTTPException(status_code=404, detail="Пермиты не найдены")
    
    # Конвертируем is_owner_builder
    for p in permits:
        if p.get('is_owner_builder') is not None:
            p['is_owner_builder'] = 'Yes' if p['is_owner_builder'] else 'No'
        else:
            p['is_owner_builder'] = 'Unknown'
    
    suffix = "_owners" if only_owners else ""
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=permits[0].keys())
        writer.writeheader()
        writer.writerows(permits)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=permits_job_{job_id}{suffix}.csv"}
        )
    else:
        return {"permits": permits, "total": len(permits)}


@router.get("/export")
async def export_all(
    format: str = Query(default="csv", enum=["csv", "json"]),
    is_owner_builder: Optional[bool] = None,
    min_cost: Optional[float] = None,
    year: Optional[int] = None
):
    """Экспорт всех пермитов с фильтрами"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if is_owner_builder is not None:
        conditions.append("is_owner_builder = ?")
        params.append(1 if is_owner_builder else 0)
    if min_cost is not None:
        conditions.append("est_project_cost >= ?")
        params.append(min_cost)
    if year:
        conditions.append("strftime('%Y', applied_date) = ?")
        params.append(str(year))
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT permit_num, permit_class, permit_type_mapped, description,
               est_project_cost, applied_date, address, city, state, zipcode,
               contractor_name, is_owner_builder, verification_status, 
               work_performer_text, portal_link, created_at
        FROM permits
        WHERE {where}
        ORDER BY applied_date DESC
    """, params)
    permits = cursor.fetchall()
    conn.close()
    
    if not permits:
        raise HTTPException(status_code=404, detail="Пермиты не найдены")
    
    # Конвертируем is_owner_builder
    for p in permits:
        if p.get('is_owner_builder') is not None:
            p['is_owner_builder'] = 'Yes' if p['is_owner_builder'] else 'No'
        else:
            p['is_owner_builder'] = 'Unknown'
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=permits[0].keys())
        writer.writeheader()
        writer.writerows(permits)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=permits_export_{timestamp}.csv"}
        )
    else:
        return {"permits": permits, "total": len(permits)}
