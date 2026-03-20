"""
MyBuildingPermit API Router
Endpoints для парсинга данных с permitsearch.mybuildingpermit.com
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from typing import List, Optional
import csv
import io
import json
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_connection, dict_factory, create_mbp_job, update_mbp_job, insert_mbp_permit
from utils.excel_export import create_formatted_excel
from schemas import (
    MBPParseRequest,
    MBPJobStatus,
    MBPJobListItem,
    MBPPermit,
    MBPPermitsResponse,
    MBPStats,
    MBP_JURISDICTIONS,
)
try:
    from backend.core.parser_settings_store import get_parser_settings
except ImportError:
    from core.parser_settings_store import get_parser_settings

router = APIRouter()


@router.get("/jurisdictions")
async def get_jurisdictions():
    """Получить список доступных юрисдикций"""
    return {"jurisdictions": MBP_JURISDICTIONS}


@router.post("/parse", response_model=dict)
async def start_parse(request: MBPParseRequest):
    """Запуск парсинга MyBuildingPermit"""
    print(f"\n[MBP API] ===== Starting MyBuildingPermit parse =====")
    print(f"[MBP API] Jurisdictions: {request.jurisdictions}")
    print(f"[MBP API] Days back: {request.days_back}")
    print(f"[MBP API] Limit per city: {request.limit_per_city or 'unlimited'}")
    
    try:
        defaults = get_parser_settings("mybuilding").get("config", {})
        request_jurisdictions = request.jurisdictions if request.jurisdictions else defaults.get("jurisdictions", [])
        request_days_back = request.days_back if request.days_back is not None else defaults.get("days_back", 7)
        request_headless = request.headless if request.headless is not None else not defaults.get("browser_visible", True)

        # Валидация юрисдикций
        valid_jurisdictions = [j for j in request_jurisdictions if j in MBP_JURISDICTIONS]
        if not valid_jurisdictions:
            raise HTTPException(status_code=400, detail="Нет валидных юрисдикций")
        
        # Создаём задачу
        job_id = create_mbp_job(
            jurisdictions=valid_jurisdictions,
            days_back=request_days_back
        )
        print(f"[MBP API] Created job {job_id}")
        
        # Обновляем статус на "running" сразу, чтобы UI показал прогресс
        from database import update_mbp_job
        update_mbp_job(job_id, status="running", current_jurisdiction="Initializing browser...")
        
        # Запускаем парсинг в фоне
        from services.parsers.mybuildingpermit_parser import start_mbp_parse_job
        print(f"[MBP API] Starting parse job {job_id} with headless={request_headless} (browser visible when False)")
        start_mbp_parse_job(
            job_id=job_id,
            jurisdictions=valid_jurisdictions,
            days_back=request_days_back,
            limit_per_city=request.limit_per_city,
            headless=request_headless
        )
        print(f"[MBP API] Started parse job {job_id} in background")
        
        return {
            "job_id": job_id,
            "status": "started",
            "jurisdictions": valid_jurisdictions,
            "days_back": request_days_back
        }
        
    except Exception as e:
        import traceback
        error_msg = f"Error starting MBP parse: {str(e)}"
        print(f"[MBP API] ERROR: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/status/{job_id}", response_model=MBPJobStatus)
async def get_status(job_id: int):
    """Получить статус парсинга"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM mbp_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job не найден")
    
    return MBPJobStatus(**job)


@router.get("/jobs", response_model=List[MBPJobListItem])
async def get_jobs(limit: int = 100):
    """Список всех парсингов (история)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM mbp_jobs ORDER BY started_at DESC LIMIT ?", (limit,))
    jobs = cursor.fetchall()
    conn.close()
    
    return [MBPJobListItem(**job) for job in jobs]


@router.get("/list", response_model=MBPPermitsResponse)
async def get_permits(
    job_id: Optional[int] = None,
    jurisdiction: Optional[str] = None,
    is_owner_builder: Optional[bool] = None,
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
    if jurisdiction:
        conditions.append("LOWER(p.jurisdiction) LIKE ?")
        params.append(f"%{jurisdiction.lower()}%")
    if is_owner_builder is not None:
        conditions.append("p.is_owner_builder = ?")
        params.append(1 if is_owner_builder else 0)
    if search:
        conditions.append("""
            (p.permit_number LIKE ? OR p.address LIKE ? OR p.project_name LIKE ?)
        """)
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT p.id, p.job_id, p.permit_number, p.jurisdiction, p.project_name,
               p.description, p.permit_type, p.permit_status, p.address, p.parcel,
               p.applied_date, p.issued_date, p.applicant_name, p.contractor_name,
               p.contractor_license, p.is_owner_builder, p.matches_target_type, p.permit_url, p.created_at
        FROM mbp_permits p
        WHERE {where}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """, params + [limit, skip])
    permits = cursor.fetchall()
    
    cursor.execute(f"SELECT COUNT(*) as cnt FROM mbp_permits p WHERE {where}", params)
    total = cursor.fetchone()["cnt"]
    
    conn.close()
    
    for p in permits:
        if p.get('is_owner_builder') is not None:
            p['is_owner_builder'] = bool(p['is_owner_builder'])
        if p.get('matches_target_type') is not None:
            p['matches_target_type'] = bool(p['matches_target_type'])
    
    return MBPPermitsResponse(permits=[MBPPermit(**p) for p in permits], total=total)


@router.get("/owner-builders", response_model=MBPPermitsResponse)
async def get_owner_builders(
    job_id: Optional[int] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Получить только owner-builders"""
    return await get_permits(
        job_id=job_id,
        is_owner_builder=True,
        skip=skip,
        limit=limit
    )


@router.get("/stats", response_model=MBPStats)
async def get_stats(job_id: Optional[int] = None):
    """Статистика по пермитам: всего, подходящие по типам (TARGET_CONFIG), owner-builders из них"""
    conn = get_connection()
    cursor = conn.cursor()
    
    where = f"WHERE job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"SELECT COUNT(*) FROM mbp_permits {where}")
    total = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM mbp_permits {where} {'AND' if where else 'WHERE'} COALESCE(matches_target_type, false) = true")
    matching_types = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT COUNT(*) FROM mbp_permits {where}
        {'AND' if where else 'WHERE'} COALESCE(matches_target_type, false) = true AND is_owner_builder = true
    """)
    owner_builders_from_matching = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM mbp_permits {where} {'AND' if where else 'WHERE'} is_owner_builder = true")
    owner_builders = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT jurisdiction, COUNT(*) as cnt 
        FROM mbp_permits {where}
        GROUP BY jurisdiction
        ORDER BY cnt DESC
    """)
    by_jurisdiction = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute(f"""
        SELECT COALESCE(permit_type, '—') as permit_type, COUNT(*) as cnt 
        FROM mbp_permits {where}
        GROUP BY permit_type
        ORDER BY cnt DESC
    """)
    by_type = {str(row[0]): row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return MBPStats(
        total=total,
        matching_types=matching_types,
        owner_builders_from_matching=owner_builders_from_matching,
        owner_builders=owner_builders,
        by_jurisdiction=by_jurisdiction,
        by_type=by_type,
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int):
    """Остановить задачу парсинга"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    # Проверяем существование job
    cursor.execute("SELECT * FROM mbp_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job не найден")
    
    # Обновляем статус на cancelled
    from database import update_mbp_job
    update_mbp_job(
        job_id,
        status="cancelled",
        completed_at=datetime.now().isoformat(),
        current_jurisdiction=None
    )
    
    conn.close()
    print(f"[MBP API] Job {job_id} cancelled")
    return {"status": "cancelled", "job_id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: int):
    """Удалить задачу парсинга и связанные пермиты"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем существование job
    cursor.execute("SELECT * FROM mbp_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job не найден")
    
    # Удаляем связанные пермиты
    cursor.execute("DELETE FROM mbp_permits WHERE job_id = ?", (job_id,))
    permits_deleted = cursor.rowcount
    
    # Удаляем job
    cursor.execute("DELETE FROM mbp_jobs WHERE id = ?", (job_id,))
    
    conn.commit()
    conn.close()
    
    print(f"[MBP API] Job {job_id} deleted (removed {permits_deleted} permits)")
    return {
        "status": "deleted",
        "job_id": job_id,
        "permits_deleted": permits_deleted
    }


MBP_EXPORT_COLUMNS = [
    "permit_number", "jurisdiction", "project_name", "description", "permit_type",
    "permit_status", "address", "parcel", "applied_date", "issued_date",
    "applicant_name", "contractor_name", "contractor_license", "is_owner_builder",
    "matches_target_type", "permit_url",
]


@router.get("/export")
async def export_permits(
    job_id: Optional[int] = None,
    format: str = Query(default="csv", enum=["csv", "json", "xlsx"]),
    only_owners: bool = Query(default=False)
):
    """Экспорт результатов в CSV, JSON или Excel (все вытащенные поля)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if job_id:
        conditions.append("job_id = ?")
        params.append(job_id)
    if only_owners:
        conditions.append("is_owner_builder = true")
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cursor.execute(f"""
        SELECT permit_number, jurisdiction, project_name, description, permit_type,
               permit_status, address, parcel, applied_date, issued_date,
               applicant_name, contractor_name, contractor_license, is_owner_builder,
               matches_target_type, permit_url
        FROM mbp_permits
        WHERE {where}
        ORDER BY created_at DESC
    """, params)
    permits = cursor.fetchall()
    conn.close()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_owners" if only_owners else ""
    
    # Конвертируем для читаемости в экспорте
    for p in permits:
        p['is_owner_builder'] = 'Yes' if p.get('is_owner_builder') else 'No'
        p['matches_target_type'] = 'Yes' if p.get('matches_target_type') else 'No'
    
    if format == "csv":
        if not permits:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=MBP_EXPORT_COLUMNS)
            writer.writeheader()
            raw = output.getvalue()
        else:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=MBP_EXPORT_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(permits)
            raw = output.getvalue()
        return StreamingResponse(
            iter([raw]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mbp_permits_{timestamp}{suffix}.csv"}
        )
    
    if format == "xlsx":
        excel_bytes = create_formatted_excel(
            permits,
            sheet_name="MyBuildingPermit",
            header_bg="7C3AED",
        )
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=mbp_permits_{timestamp}{suffix}.xlsx"}
        )
    
    if not permits:
        return {"permits": [], "total": 0}
    return {"permits": permits, "total": len(permits)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_mbp_job(job_id: int):
    """Остановить задачу парсинга MBP"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, status FROM mbp_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] not in ("running", "pending"):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job['status']}'")
    
    cursor.execute("""
        UPDATE mbp_jobs SET status = 'cancelled', completed_at = ?, current_jurisdiction = NULL
        WHERE id = ?
    """, (datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()
    
    return {"status": "cancelled", "job_id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_mbp_job(job_id: int):
    """Удалить задачу и связанные пермиты MBP"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM mbp_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")
    
    cursor.execute("DELETE FROM mbp_permits WHERE job_id = ?", (job_id,))
    permits_deleted = cursor.rowcount
    cursor.execute("DELETE FROM mbp_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    
    return {"status": "deleted", "job_id": job_id, "permits_deleted": permits_deleted}
