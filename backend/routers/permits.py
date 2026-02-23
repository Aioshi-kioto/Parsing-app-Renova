"""
Permits API Router
Endpoints для парсинга и получения данных Seattle Building Permits
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from typing import List, Optional
import csv
import io
import json
from datetime import datetime

from utils.excel_export import create_formatted_excel

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
    print(f"\n[PERMITS API] ===== Starting permit parse request =====")
    print(f"[PERMITS API] Year: {request.year}, Month: {request.month}")
    print(f"[PERMITS API] Permit Class: {request.permit_class}")
    print(f"[PERMITS API] Min Cost: {request.min_cost}")
    print(f"[PERMITS API] Verify Owner-Builder: {request.verify_owner_builder}, Headless: {request.headless} (browser visible when False)")
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Starting permit parse: year={request.year}, month={request.month}, "
                   f"permit_class={request.permit_class}, min_cost={request.min_cost}, "
                   f"verify={request.verify_owner_builder}")
        print(f"[PERMITS API] Logger initialized")
        
        # Нормализуем permit_class (пустая строка -> None)
        permit_class = request.permit_class if request.permit_class and request.permit_class.strip() else None
        print(f"[PERMITS API] Normalized permit_class: {permit_class}")
        
        print(f"[PERMITS API] Creating permit job...")
        job_id = create_permit_job(
            year=request.year,
            permit_class=permit_class,
            min_cost=request.min_cost
        )
        print(f"[PERMITS API] OK Created permit job {job_id}")
        logger.info(f"Created permit job {job_id}")
        
        print(f"[PERMITS API] Importing start_permit_parse_job...")
        from services.permit_parser import start_permit_parse_job
        print(f"[PERMITS API] Starting permit parse job in background...")
        start_permit_parse_job(
            job_id=job_id,
            year=request.year,
            month=request.month,
            permit_class=permit_class,
            min_cost=request.min_cost,
            verify=request.verify_owner_builder,
            headless=request.headless
        )
        print(f"[PERMITS API] OK Started permit parse job {job_id} in background thread")
        logger.info(f"Started permit parse job {job_id}")
        
        result = {
            "job_id": job_id,
            "status": "started",
            "year": request.year,
            "month": request.month,
            "permit_class": permit_class
        }
        print(f"[PERMITS API] ===== Request completed successfully =====\n")
        return result
        
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_msg = f"Error starting permit parse: {str(e)}"
        error_traceback = traceback.format_exc()
        
        print(f"\n[PERMITS API] ERROR")
        print(f"[PERMITS API] {error_msg}")
        print(f"[PERMITS API] Traceback:\n{error_traceback}")
        print(f"[PERMITS API] ============================================\n")
        
        logger.error(error_msg)
        logger.error(error_traceback)
        raise HTTPException(status_code=500, detail=error_msg)


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
        SELECT id, status, year, permits_found, permits_verified, owner_builders_found, error_message, started_at, completed_at
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
               p.verification_status, p.work_performer_text, p.contacts_text, p.portal_link,
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
    
    # Счётчики — по ВСЕМ пермитам (не только с cost)
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_owner_builder = 1 THEN 1 ELSE 0 END) as owner_builders,
            SUM(CASE WHEN is_owner_builder = 0 THEN 1 ELSE 0 END) as contractors,
            SUM(CASE WHEN is_owner_builder IS NULL THEN 1 ELSE 0 END) as unknown
        FROM permits
        WHERE {where}
    """, params)
    row_counts = cursor.fetchone()
    
    # Стоимость — только по пермитам с est_project_cost
    cursor.execute(f"""
        SELECT 
            AVG(est_project_cost) as avg_cost,
            MIN(est_project_cost) as min_cost,
            MAX(est_project_cost) as max_cost,
            SUM(est_project_cost) as total_cost
        FROM permits
        WHERE {where} AND est_project_cost IS NOT NULL
    """, params)
    row_cost = cursor.fetchone()
    conn.close()
    
    return PermitStats(
        total=row_counts[0] or 0,
        owner_builders=row_counts[1] or 0,
        contractors=row_counts[2] or 0,
        unknown=row_counts[3] or 0,
        avg_cost=round(row_cost[0], 2) if row_cost[0] else 0,
        min_cost=row_cost[1],
        max_cost=row_cost[2],
        total_cost=round(row_cost[3], 2) if row_cost[3] else 0,
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
        SELECT permit_num, permit_class, permit_type_mapped, permit_type_desc, description,
               est_project_cost, applied_date, issued_date, status_current,
               address, city, state, zipcode,
               contractor_name, is_owner_builder, verification_status, 
               work_performer_text, contacts_text, portal_link, created_at
        FROM permits
        WHERE job_id = ? {owner_filter}
        ORDER BY applied_date DESC
    """, (job_id,))
    permits = cursor.fetchall()
    conn.close()
    
    if not permits:
        raise HTTPException(status_code=404, detail="Пермиты не найдены")
    
    export_columns = [
        "permit_num", "permit_class", "permit_type_mapped", "permit_type_desc", "description",
        "est_project_cost", "applied_date", "issued_date", "status_current",
        "address", "city", "state", "zipcode", "contractor_name",
        "owner_builder", "contacts_text", "verification_status", "portal_link", "created_at",
    ]
    rows_export = []
    for p in permits:
        if p.get("work_performer_text"):
            val = p["work_performer_text"]
        elif p.get("is_owner_builder") is not None:
            val = "Yes" if p["is_owner_builder"] else "No"
        else:
            val = "Unknown"
        rows_export.append({k: p.get(k) if k != "owner_builder" else val for k in export_columns})
    
    suffix = "_owners" if only_owners else ""
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_export)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=permits_job_{job_id}{suffix}.csv"}
        )
    else:
        return {"permits": rows_export, "total": len(rows_export)}


@router.get("/export")
async def export_all(
    format: str = Query(default="csv", enum=["csv", "json", "xlsx"]),
    is_owner_builder: Optional[bool] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    city: Optional[str] = None,
    permit_class: Optional[str] = None,
    search: Optional[str] = None,
    year: Optional[int] = None,
):
    """Экспорт всех пермитов с фильтрами (CSV, JSON, Excel)"""
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
    if max_cost is not None:
        conditions.append("est_project_cost <= ?")
        params.append(max_cost)
    if city:
        conditions.append("LOWER(city) LIKE ?")
        params.append(f"%{city.lower()}%")
    if permit_class:
        conditions.append("LOWER(permit_class) LIKE ?")
        params.append(f"%{permit_class.lower()}%")
    if search:
        conditions.append("(permit_num LIKE ? OR address LIKE ? OR description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if year:
        conditions.append("strftime('%Y', applied_date) = ?")
        params.append(str(year))
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT permit_num, permit_class, permit_type_mapped, permit_type_desc, description,
               est_project_cost, applied_date, issued_date, status_current,
               address, city, state, zipcode,
               contractor_name, is_owner_builder, verification_status,
               work_performer_text, contacts_text, portal_link, created_at
        FROM permits
        WHERE {where}
        ORDER BY applied_date DESC
    """, params)
    permits = cursor.fetchall()
    conn.close()
    
    if not permits:
        raise HTTPException(status_code=404, detail="Пермиты не найдены")
    
    # Одна колонка "Owner Builder": текст из верификации (Owner/Lessee, Licensed Contractor и т.д.) или Yes/No/Unknown
    export_columns = [
        "permit_num", "permit_class", "permit_type_mapped", "permit_type_desc", "description",
        "est_project_cost", "applied_date", "issued_date", "status_current",
        "address", "city", "state", "zipcode", "contractor_name",
        "owner_builder", "contacts_text", "verification_status", "portal_link", "created_at",
    ]
    rows_export = []
    for p in permits:
        if p.get("work_performer_text"):
            val = p["work_performer_text"]
        elif p.get("is_owner_builder") is not None:
            val = "Yes" if p["is_owner_builder"] else "No"
        else:
            val = "Unknown"
        row = {k: p.get(k) for k in export_columns if k not in ("owner_builder", "contacts_text")}
        row["owner_builder"] = val
        row["contacts_text"] = p.get("contacts_text")
        # порядок колонок как в export_columns
        rows_export.append({k: row.get(k) for k in export_columns})
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_export)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=permits_export_{timestamp}.csv"}
        )
    elif format == "xlsx":
        excel_bytes = create_formatted_excel(
            rows_export,
            sheet_name="Building Permits",
            currency_columns=["est_project_cost"],
            header_bg="7C3AED",
        )
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=permits_export_{timestamp}.xlsx"}
        )
    else:
        return {"permits": rows_export, "total": len(rows_export)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_permit_job(job_id: int):
    """Остановить задачу парсинга пермитов"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, status FROM permit_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] not in ("running", "pending", "fetching", "processing", "verifying"):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job['status']}'")
    
    cursor.execute("""
        UPDATE permit_jobs SET status = 'cancelled', completed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()
    
    return {"status": "cancelled", "job_id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_permit_job(job_id: int):
    """Удалить задачу и связанные пермиты"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM permit_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    cursor.execute("DELETE FROM permits WHERE job_id = ?", (job_id,))
    permits_deleted = cursor.rowcount
    cursor.execute("DELETE FROM permit_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    
    return {"status": "deleted", "job_id": job_id, "permits_deleted": permits_deleted}
