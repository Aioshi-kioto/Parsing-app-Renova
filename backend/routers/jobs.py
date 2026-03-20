"""
Unified Jobs API
Returns jobs from all parser job tables in a single list.
"""
from fastapi import APIRouter, Query
from typing import Optional
import json

try:
    from backend.database import get_connection, dict_factory
    from backend.core.parser_settings_store import get_parser_settings
except ImportError:
    from database import get_connection, dict_factory
    from core.parser_settings_store import get_parser_settings

router = APIRouter()


def _safe_query(cursor, sql):
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception:
        return []


@router.get("")
async def list_jobs(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Unified list of all jobs across parsers."""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    jobs = []
    permit_settings = get_parser_settings("permit")
    mbp_settings = get_parser_settings("mybuilding")

    try:
        # Zillow jobs
        zillow_rows = _safe_query(cursor, """
            SELECT id, 'ZILLOW_PARSE' as type, status, started_at, completed_at as finished_at,
                   homes_found as result_count, 
                   CASE WHEN status IN ('running','parsing','verifying','pending') THEN 50 
                        WHEN status = 'completed' THEN 100 ELSE 0 END as progress,
                   NULL as error
            FROM zillow_jobs ORDER BY started_at DESC LIMIT 50
        """)
        for r in zillow_rows:
            r["result_summary"] = f"{r.get('result_count') or 0} homes"
            r["duration"] = _calc_duration(r.get("started_at"), r.get("finished_at"))
            jobs.append(r)

        # Permit jobs
        permit_rows = _safe_query(cursor, """
            SELECT id, 'SDCI_PARSE' as type, status, started_at, completed_at as finished_at,
                   year, permit_class_filter, min_cost, permits_found, permits_verified, owner_builders_found,
                   permits_found as result_count,
                   CASE WHEN status IN ('running','parsing','verifying','pending') THEN 50
                        WHEN status = 'completed' THEN 100 ELSE 0 END as progress,
                   error_message as error
            FROM permit_jobs ORDER BY started_at DESC LIMIT 50
        """)
        for r in permit_rows:
            cfg = {
                "year": r.get("year"),
                "permit_class": r.get("permit_class_filter"),
                "min_cost": r.get("min_cost"),
                "verify_owner_builder": permit_settings.get("config", {}).get("verify_owner_builder", True),
                "browser_visible": permit_settings.get("config", {}).get("browser_visible", True),
            }
            result = {
                "permits_found": r.get("permits_found") or 0,
                "permits_verified": r.get("permits_verified") or 0,
                "owner_builders_found": r.get("owner_builders_found") or 0,
            }
            r["result_summary"] = f"{r.get('result_count') or 0} permits"
            r["duration"] = _calc_duration(r.get("started_at"), r.get("finished_at"))
            r["parser_name"] = "Пермит"
            r["config"] = cfg
            r["result"] = result
            r["channels"] = permit_settings.get("channels", {})
            r["fixed_settings"] = permit_settings.get("fixed_settings", {})
            jobs.append(r)

        # MBP jobs
        mbp_rows = _safe_query(cursor, """
            SELECT id, 'MBP_PARSE' as type, status, started_at, completed_at as finished_at,
                   jurisdictions, days_back, total_permits, analyzed_count, owner_builders_found,
                   total_permits as result_count,
                   CASE WHEN status IN ('running','parsing','verifying','pending') THEN 50
                        WHEN status = 'completed' THEN 100 ELSE 0 END as progress,
                   error_message as error
            FROM mbp_jobs ORDER BY started_at DESC LIMIT 50
        """)
        for r in mbp_rows:
            jurisdictions = r.get("jurisdictions")
            if isinstance(jurisdictions, str):
                try:
                    jurisdictions = json.loads(jurisdictions)
                except Exception:
                    jurisdictions = [jurisdictions]
            cfg = {
                "jurisdictions": jurisdictions or [],
                "days_back": r.get("days_back"),
                "browser_visible": mbp_settings.get("config", {}).get("browser_visible", True),
            }
            result = {
                "total_permits": r.get("total_permits") or 0,
                "analyzed_count": r.get("analyzed_count") or 0,
                "owner_builders_found": r.get("owner_builders_found") or 0,
            }
            r["result_summary"] = f"{r.get('result_count') or 0} permits"
            r["duration"] = _calc_duration(r.get("started_at"), r.get("finished_at"))
            r["parser_name"] = "MyBuilding"
            r["config"] = cfg
            r["result"] = result
            r["channels"] = mbp_settings.get("channels", {})
            r["fixed_settings"] = mbp_settings.get("fixed_settings", {})
            jobs.append(r)

        # Scheduled operations (future or queued dispatch)
        scheduled_rows = _safe_query(cursor, """
            SELECT id, operation_type, status, run_at_utc, payload_json, channels_json, fixed_settings_json,
                   created_at, dispatched_job_id, dispatched_table, dispatch_error
            FROM scheduled_operations
            ORDER BY run_at_utc ASC
            LIMIT 100
        """)
        for r in scheduled_rows:
            op_type = (r.get("operation_type") or "").lower()
            parser_name = "Пермит" if op_type == "permit" else "MyBuilding" if op_type == "mybuilding" else op_type
            channels = r.get("channels_json")
            if isinstance(channels, str):
                try:
                    channels = json.loads(channels)
                except Exception:
                    channels = {}
            fixed_settings = r.get("fixed_settings_json")
            if isinstance(fixed_settings, str):
                try:
                    fixed_settings = json.loads(fixed_settings)
                except Exception:
                    fixed_settings = {}
            config = r.get("payload_json")
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except Exception:
                    config = {}
            status_val = r.get("status")
            if status_val == "dispatching":
                status_val = "queued"
            result_summary = "Запуск по расписанию"
            if r.get("dispatched_job_id"):
                result_summary = f"Создан job #{r.get('dispatched_job_id')}"
            if r.get("dispatch_error"):
                result_summary = str(r.get("dispatch_error"))[:120]

            jobs.append({
                "id": r.get("id"),
                "type": "SCHEDULED_OPERATION",
                "status": status_val,
                "scheduled_at": r.get("run_at_utc"),
                "started_at": r.get("created_at"),
                "finished_at": None,
                "result_count": None,
                "progress": 0,
                "error": r.get("dispatch_error"),
                "result_summary": result_summary,
                "duration": "--",
                "parser_name": parser_name,
                "config": config or {},
                "result": {},
                "channels": channels or {},
                "fixed_settings": fixed_settings or {},
                "operation_type": op_type,
                "is_scheduled_operation": True,
            })

    except Exception as e:
        print(f"[JOBS] Error fetching jobs: {e}")
    finally:
        conn.close()

    # Sort: scheduled by nearest run_at first, otherwise by started_at desc
    def sort_key(row):
        if row.get("is_scheduled_operation"):
            return (0, row.get("scheduled_at") or "")
        return (1, row.get("started_at") or "")

    jobs.sort(key=sort_key, reverse=False)

    # Filter
    if status:
        statuses = status.split("|")
        jobs = [j for j in jobs if j.get("status") in statuses]
    if type:
        types = type.lower().split("|")
        jobs = [j for j in jobs if any(t in j.get("type", "").lower() for t in types)]

    return {"jobs": jobs[:limit]}


@router.get("/{job_id}")
async def get_job_detail(job_id: int, parser_type: Optional[str] = Query(None)):
    """Get detailed info for a specific job."""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    parser_type = (parser_type or "").lower().strip()
    table_map = {
        "permit": ("permit_jobs", "SDCI_PARSE"),
        "mybuilding": ("mbp_jobs", "MBP_PARSE"),
        "mbp": ("mbp_jobs", "MBP_PARSE"),
        "zillow": ("zillow_jobs", "ZILLOW_PARSE"),
    }

    try:
        if parser_type == "scheduled":
            cursor.execute("SELECT * FROM scheduled_operations WHERE id = ?", (job_id,))
            srow = cursor.fetchone()
            if srow:
                channels = srow.get("channels_json")
                if isinstance(channels, str):
                    try:
                        channels = json.loads(channels)
                    except Exception:
                        channels = {}
                fixed_settings = srow.get("fixed_settings_json")
                if isinstance(fixed_settings, str):
                    try:
                        fixed_settings = json.loads(fixed_settings)
                    except Exception:
                        fixed_settings = {}
                config = srow.get("payload_json")
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except Exception:
                        config = {}
                op_type = (srow.get("operation_type") or "").lower()
                return {
                    "id": srow.get("id"),
                    "type": "SCHEDULED_OPERATION",
                    "parser_name": "Пермит" if op_type == "permit" else "MyBuilding" if op_type == "mybuilding" else op_type,
                    "status": srow.get("status"),
                    "scheduled_at": srow.get("run_at_utc"),
                    "started_at": srow.get("created_at"),
                    "finished_at": None,
                    "error": srow.get("dispatch_error"),
                    "duration": "--",
                    "config": config or {},
                    "result": {},
                    "channels": channels or {},
                    "fixed_settings": fixed_settings or {},
                    "operation_type": op_type,
                    "is_scheduled_operation": True,
                    "dispatched_job_id": srow.get("dispatched_job_id"),
                }

        search_tables = [table_map[parser_type]] if parser_type in table_map else [
            ("zillow_jobs", "ZILLOW_PARSE"),
            ("permit_jobs", "SDCI_PARSE"),
            ("mbp_jobs", "MBP_PARSE"),
        ]

        for tbl, jtype in search_tables:
            try:
                cursor.execute(f"SELECT * FROM {tbl} WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    parser_key = "permit" if tbl == "permit_jobs" else "mybuilding" if tbl == "mbp_jobs" else "zillow"
                    settings = get_parser_settings("permit") if parser_key == "permit" else (
                        get_parser_settings("mybuilding") if parser_key == "mybuilding" else {"channels": {}, "fixed_settings": {}}
                    )

                    if parser_key == "permit":
                        config = {
                            "year": row.get("year"),
                            "month": settings.get("config", {}).get("month"),
                            "permit_class": row.get("permit_class_filter"),
                            "min_cost": row.get("min_cost"),
                            "verify_owner_builder": settings.get("config", {}).get("verify_owner_builder", True),
                            "browser_visible": settings.get("config", {}).get("browser_visible", True),
                        }
                        result = {
                            "permits_found": row.get("permits_found") or 0,
                            "permits_verified": row.get("permits_verified") or 0,
                            "owner_builders_found": row.get("owner_builders_found") or 0,
                        }
                        parser_name = "Пермит"
                    elif parser_key == "mybuilding":
                        jurisdictions = row.get("jurisdictions")
                        if isinstance(jurisdictions, str):
                            try:
                                jurisdictions = json.loads(jurisdictions)
                            except Exception:
                                jurisdictions = [jurisdictions]
                        config = {
                            "jurisdictions": jurisdictions or [],
                            "days_back": row.get("days_back"),
                            "browser_visible": settings.get("config", {}).get("browser_visible", True),
                        }
                        result = {
                            "total_permits": row.get("total_permits") or 0,
                            "analyzed_count": row.get("analyzed_count") or 0,
                            "owner_builders_found": row.get("owner_builders_found") or 0,
                        }
                        parser_name = "MyBuilding"
                    else:
                        config = {}
                        result = {}
                        parser_name = "Zillow"

                    return {
                        "id": row.get("id"),
                        "type": jtype,
                        "parser_name": parser_name,
                        "status": row.get("status"),
                        "started_at": row.get("started_at"),
                        "finished_at": row.get("completed_at"),
                        "error": row.get("error_message"),
                        "duration": _calc_duration(row.get("started_at"), row.get("completed_at")),
                        "config": config,
                        "result": result,
                        "channels": settings.get("channels", {}),
                        "fixed_settings": settings.get("fixed_settings", {}),
                    }
            except Exception:
                pass
    finally:
        conn.close()

    return {"error": "Job not found", "id": job_id}


def _calc_duration(started, finished):
    if not started:
        return "--"
    from datetime import datetime
    try:
        start = datetime.fromisoformat(str(started)) if not isinstance(started, datetime) else started
        if finished:
            end = datetime.fromisoformat(str(finished)) if not isinstance(finished, datetime) else finished
        else:
            end = datetime.utcnow()
        delta = int((end - start).total_seconds())
        if delta < 60:
            return f"{delta}s"
        return f"{delta // 60}m {delta % 60}s"
    except Exception:
        return "--"
