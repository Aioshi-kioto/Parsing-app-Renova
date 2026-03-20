from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from backend.services.scheduled_operations_service import (
        ALLOWED_TYPES,
        cancel_scheduled_operation,
        create_scheduled_operation,
        dispatch_operation_now,
        get_scheduled_operation,
        list_scheduled_operations,
        update_scheduled_operation,
    )
except ImportError:
    from services.scheduled_operations_service import (
        ALLOWED_TYPES,
        cancel_scheduled_operation,
        create_scheduled_operation,
        dispatch_operation_now,
        get_scheduled_operation,
        list_scheduled_operations,
        update_scheduled_operation,
    )


router = APIRouter()


class ScheduledOperationCreatePayload(BaseModel):
    operation_type: str = Field(..., description="permit|mybuilding")
    run_at_utc: datetime
    timezone: str = "UTC"
    payload: Dict[str, Any] = {}
    channels: Dict[str, bool] = {}
    fixed_settings: Dict[str, Any] = {}
    created_by: Optional[str] = None
    dedupe_key: Optional[str] = None


class ScheduledOperationUpdatePayload(BaseModel):
    channels: Optional[Dict[str, bool]] = None
    payload: Optional[Dict[str, Any]] = None
    updated_by: Optional[str] = None


class ScheduledOperationCancelPayload(BaseModel):
    cancelled_by: Optional[str] = None
    reason: Optional[str] = None


def _validate_operation_type(value: str) -> str:
    t = (value or "").strip().lower()
    if t not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"operation_type must be one of: {', '.join(sorted(ALLOWED_TYPES))}")
    return t


@router.post("")
async def create_operation(payload: ScheduledOperationCreatePayload):
    operation_type = _validate_operation_type(payload.operation_type)
    run_at = payload.run_at_utc
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=timezone.utc)

    try:
        row = create_scheduled_operation(
            operation_type=operation_type,
            run_at_utc=run_at,
            timezone_name=payload.timezone,
            payload=payload.payload,
            channels=payload.channels,
            fixed_settings=payload.fixed_settings,
            created_by=payload.created_by,
            dedupe_key=payload.dedupe_key,
        )
        return {"ok": True, "operation": row}
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("")
async def list_operations(
    status: Optional[str] = Query(None),
    operation_type: Optional[str] = Query(None),
    include_past: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    if operation_type:
        operation_type = _validate_operation_type(operation_type)
    rows = list_scheduled_operations(
        status=status,
        operation_type=operation_type,
        include_past=include_past,
        limit=limit,
    )
    return {"operations": rows}


@router.get("/{op_id}")
async def get_operation(op_id: int):
    row = get_scheduled_operation(op_id)
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")
    return row


@router.patch("/{op_id}")
async def patch_operation(op_id: int, body: ScheduledOperationUpdatePayload):
    try:
        row = update_scheduled_operation(op_id, channels=body.channels, payload=body.payload, updated_by=body.updated_by)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if not row:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    return {"ok": True, "operation": row}


@router.post("/{op_id}/cancel")
async def cancel_operation(op_id: int, payload: ScheduledOperationCancelPayload):
    updated = cancel_scheduled_operation(op_id, payload.cancelled_by, payload.reason)
    if updated == 0:
        raise HTTPException(status_code=409, detail="Operation cannot be cancelled from current status")
    return {"ok": True, "id": op_id}


@router.post("/{op_id}/run-now")
async def run_now(op_id: int):
    try:
        row = dispatch_operation_now(op_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")
    return {"ok": True, "operation": row}
