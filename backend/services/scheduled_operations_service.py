import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from backend.database import get_connection, dict_factory, create_mbp_job, create_permit_job
except ImportError:
    from database import get_connection, dict_factory, create_mbp_job, create_permit_job


ALLOWED_TYPES = {"permit", "mybuilding"}
ALLOWED_STATUSES = {"scheduled", "dispatching", "dispatched", "failed", "cancelled", "dead"}


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def _safe_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return default


def _normalize(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "operation_type": row.get("operation_type"),
        "status": row.get("status"),
        "run_at_utc": _to_iso(row.get("run_at_utc")),
        "timezone": row.get("timezone"),
        "payload": _safe_json(row.get("payload_json"), {}),
        "channels": _safe_json(row.get("channels_json"), {}),
        "fixed_settings": _safe_json(row.get("fixed_settings_json"), {}),
        "created_by": row.get("created_by"),
        "updated_by": row.get("updated_by"),
        "cancelled_by": row.get("cancelled_by"),
        "cancel_reason": row.get("cancel_reason"),
        "created_at": _to_iso(row.get("created_at")),
        "updated_at": _to_iso(row.get("updated_at")),
        "dispatched_job_id": row.get("dispatched_job_id"),
        "dispatched_table": row.get("dispatched_table"),
        "dispatch_error": row.get("dispatch_error"),
        "attempt_count": row.get("attempt_count") or 0,
        "last_attempt_at": _to_iso(row.get("last_attempt_at")),
        "next_retry_at": _to_iso(row.get("next_retry_at")),
        "dedupe_key": row.get("dedupe_key"),
        "version": row.get("version") or 1,
    }


def create_scheduled_operation(
    operation_type: str,
    run_at_utc: datetime,
    timezone_name: str,
    payload: Dict[str, Any],
    channels: Dict[str, bool],
    fixed_settings: Dict[str, Any],
    created_by: Optional[str] = None,
    dedupe_key: Optional[str] = None,
) -> Dict[str, Any]:
    if operation_type not in ALLOWED_TYPES:
        raise ValueError("Unsupported operation_type")
    if run_at_utc.tzinfo is None:
        raise ValueError("run_at_utc must be timezone-aware")

    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scheduled_operations (
            operation_type, status, run_at_utc, timezone, payload_json, channels_json, fixed_settings_json,
            created_by, updated_by, created_at, updated_at, dedupe_key, version
        )
        VALUES (?, 'scheduled', ?, ?, ?::jsonb, ?::jsonb, ?::jsonb, ?, ?, NOW(), NOW(), ?, 1)
        RETURNING *
        """,
        (
            operation_type,
            run_at_utc.astimezone(timezone.utc).isoformat(),
            timezone_name or "UTC",
            json.dumps(payload or {}),
            json.dumps(channels or {}),
            json.dumps(fixed_settings or {}),
            created_by,
            created_by,
            dedupe_key,
        ),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return _normalize(row)


def list_scheduled_operations(
    status: Optional[str] = None,
    operation_type: Optional[str] = None,
    include_past: bool = False,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    where = ["1=1"]
    params: List[Any] = []
    if status:
        where.append("status = ?")
        params.append(status)
    if operation_type:
        where.append("operation_type = ?")
        params.append(operation_type)
    if not include_past:
        where.append("run_at_utc >= NOW() OR status IN ('scheduled','dispatching')")

    cursor.execute(
        f"""
        SELECT * FROM scheduled_operations
        WHERE {' AND '.join(where)}
        ORDER BY run_at_utc ASC
        LIMIT ?
        """,
        params + [limit],
    )
    rows = cursor.fetchall()
    conn.close()
    return [_normalize(r) for r in rows]


def get_scheduled_operation(op_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduled_operations WHERE id = ?", (op_id,))
    row = cursor.fetchone()
    conn.close()
    return _normalize(row) if row else None


def cancel_scheduled_operation(op_id: int, cancelled_by: Optional[str], reason: Optional[str]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE scheduled_operations
        SET status='cancelled', cancelled_by=?, cancel_reason=?, updated_at=NOW(), version=version+1
        WHERE id=? AND status IN ('scheduled','dispatching','failed')
        """,
        (cancelled_by, reason, op_id),
    )
    count = cursor.rowcount or 0
    conn.commit()
    conn.close()
    return count


def mark_dispatching(op_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE scheduled_operations
        SET status='dispatching', updated_at=NOW(), last_attempt_at=NOW(), attempt_count=attempt_count+1, version=version+1
        WHERE id=? AND status='scheduled'
        """,
        (op_id,),
    )
    ok = (cursor.rowcount or 0) > 0
    conn.commit()
    conn.close()
    return ok


def mark_dispatched(op_id: int, job_id: int, table_name: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE scheduled_operations
        SET status='dispatched', dispatched_job_id=?, dispatched_table=?, dispatch_error=NULL, updated_at=NOW(), version=version+1
        WHERE id=?
        """,
        (job_id, table_name, op_id),
    )
    conn.commit()
    conn.close()


def mark_dispatch_failed(op_id: int, error: str, retry_after_seconds: int = 60) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE scheduled_operations
        SET status='failed', dispatch_error=?, next_retry_at=NOW() + (? || ' seconds')::interval, updated_at=NOW(), version=version+1
        WHERE id=?
        """,
        ((error or "")[:1000], int(retry_after_seconds), op_id),
    )
    conn.commit()
    conn.close()


def dispatch_operation_now(op_id: int) -> Optional[Dict[str, Any]]:
    row = get_scheduled_operation(op_id)
    if not row:
        return None
    if row["status"] not in ("scheduled", "failed", "dispatching"):
        raise ValueError("Operation cannot be dispatched from current status")

    if row["status"] in ("scheduled", "failed"):
        if not mark_dispatching(op_id):
            raise ValueError("Operation is not in scheduled state")

    payload = row.get("payload") or {}
    op_type = row["operation_type"]
    try:
        if op_type == "permit":
            job_id = create_permit_job(
                year=payload.get("year") or datetime.utcnow().year,
                permit_class=payload.get("permit_class"),
                min_cost=payload.get("min_cost") or 5000,
            )
            mark_dispatched(op_id, job_id, "permit_jobs")
        elif op_type == "mybuilding":
            jurisdictions = payload.get("jurisdictions") or []
            days_back = payload.get("days_back") or 7
            job_id = create_mbp_job(jurisdictions=jurisdictions, days_back=days_back)
            mark_dispatched(op_id, job_id, "mbp_jobs")
        else:
            raise ValueError("Unsupported operation_type")
    except Exception as error:
        mark_dispatch_failed(op_id, str(error))
        raise

    return get_scheduled_operation(op_id)


def update_scheduled_operation(
    op_id: int,
    channels: Optional[Dict[str, bool]] = None,
    payload: Optional[Dict[str, Any]] = None,
    updated_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Partially update a scheduled operation (channels, payload)."""
    row = get_scheduled_operation(op_id)
    if not row:
        return None
    if row["status"] not in ("scheduled", "failed"):
        raise ValueError("Можно редактировать только операции в статусе scheduled/failed")

    sets: List[str] = []
    params: List[Any] = []

    if channels is not None:
        sets.append("channels_json = ?::jsonb")
        params.append(json.dumps(channels))
    if payload is not None:
        sets.append("payload_json = ?::jsonb")
        params.append(json.dumps(payload))
    if updated_by is not None:
        sets.append("updated_by = ?")
        params.append(updated_by)

    if not sets:
        return row

    sets.append("updated_at = NOW()")
    sets.append("version = version + 1")
    params.append(op_id)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE scheduled_operations SET {', '.join(sets)} WHERE id = ?",
        tuple(params),
    )
    conn.commit()
    conn.close()
    return get_scheduled_operation(op_id)


def claim_due_operations(limit: int = 20) -> List[int]:
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH due AS (
            SELECT id
            FROM scheduled_operations
            WHERE status IN ('scheduled','failed')
              AND (run_at_utc <= NOW() OR (next_retry_at IS NOT NULL AND next_retry_at <= NOW()))
            ORDER BY run_at_utc ASC
            LIMIT ?
            FOR UPDATE SKIP LOCKED
        )
        UPDATE scheduled_operations s
        SET status='dispatching',
            updated_at=NOW(),
            last_attempt_at=NOW(),
            attempt_count=attempt_count + 1,
            version=version + 1
        FROM due
        WHERE s.id = due.id
        RETURNING s.id
        """,
        (limit,),
    )
    rows = cursor.fetchall() or []
    conn.commit()
    conn.close()
    return [int(r["id"]) for r in rows]
