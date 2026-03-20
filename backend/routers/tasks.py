"""
Tasks Router
Очередь звонков (Call Queue) для Sprint 1.
"""
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database_setup import get_db
from db_models import Lead

router = APIRouter()


class TaskOut(BaseModel):
    id: str
    address: str
    case_type: str
    priority: str
    status: str
    call_due_at: datetime | None = None
    contact_name: str | None = None
    contact_phone: str | None = None

    class Config:
        from_attributes = True


class SnoozeRequest(BaseModel):
    hours: int = 24


@router.get("/today", response_model=List[TaskOut])
async def tasks_today(db: Session = Depends(get_db)):
    """
    Лиды для звонков сегодня:
    call_due_at <= now и статус в active calling pipeline.
    """
    now = datetime.now(timezone.utc)
    rows = (
        db.query(Lead)
        .filter(
            Lead.call_due_at <= now,
            Lead.status.in_(["letter_sent", "email_sent", "approved"]),
        )
        .order_by(Lead.priority.desc(), Lead.call_due_at.asc())
        .all()
    )
    return rows


@router.post("/{lead_id}/snooze")
async def snooze_task(lead_id: str, body: SnoozeRequest, db: Session = Depends(get_db)):
    """Перенести задачу звонка на X часов (по умолчанию 24)."""
    lead = db.query(Lead).filter(Lead.id == str(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.call_due_at = datetime.now(timezone.utc) + timedelta(hours=body.hours)
    db.commit()
    return {"id": str(lead.id), "call_due_at": lead.call_due_at.isoformat()}

