"""
Leads Router — CRUD API для лидов и задач на звонки.

Все эндпоинты работают через SQLAlchemy ORM + PostgreSQL.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from pydantic import BaseModel

import sys
import os

# Добавляем путь для импорта из backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_setup import get_db
from db_models import Lead, OutboundLog


# ==============================
# Pydantic схемы
# ==============================

class LeadOut(BaseModel):
    id: str
    address: str
    city: Optional[str] = None
    zip: Optional[str] = None
    case_type: str
    priority: str
    source: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    is_approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    found_at: Optional[datetime] = None
    letter_sent_at: Optional[datetime] = None
    email_sent_at: Optional[datetime] = None
    call_due_at: Optional[datetime] = None
    notes: Optional[str] = None
    matched_cases: Optional[List[str]] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


class NotesUpdate(BaseModel):
    notes: str


class ApproveRequest(BaseModel):
    approved_by: str = "admin"
    reason: Optional[str] = None


class SnoozeRequest(BaseModel):
    hours: int = 24


# ==============================
# Router
# ==============================

router = APIRouter()


@router.get("", response_model=List[LeadOut])
async def list_leads(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    case_type: Optional[str] = Query(None, description="Фильтр по кейсу"),
    priority: Optional[str] = Query(None, description="Фильтр по приоритету (RED/YELLOW/GREEN)"),
    source: Optional[str] = Query(None, description="Фильтр по источнику"),
    search: Optional[str] = Query(None, description="Поиск по адресу/имени"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Список лидов с фильтрами и пагинацией."""
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)
    if case_type:
        query = query.filter(Lead.case_type == case_type)
    if priority:
        query = query.filter(Lead.priority == priority.upper())
    if source:
        query = query.filter(Lead.source == source)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Lead.address.ilike(pattern),
                Lead.contact_name.ilike(pattern),
            )
        )

    query = query.order_by(desc(Lead.found_at))
    offset = (page - 1) * limit
    leads = query.offset(offset).limit(limit).all()
    return leads


@router.get("/tasks/today", response_model=List[LeadOut])
async def get_tasks_today(db: Session = Depends(get_db)):
    """Лиды для звонков сегодня (call_due_at <= NOW), RED первыми."""
    now = datetime.now(timezone.utc)
    leads = (
        db.query(Lead)
        .filter(
            Lead.call_due_at <= now,
            Lead.status.in_(["letter_sent", "email_sent", "approved"]),
        )
        .order_by(
            # RED первыми, потом YELLOW, потом GREEN
            Lead.priority.desc(),
            Lead.call_due_at.asc(),
        )
        .all()
    )
    return leads


@router.get("/pending-review", response_model=List[LeadOut])
async def get_pending_review(db: Session = Depends(get_db)):
    """Лиды, ожидающие ручного апрува (Semi-Autonomous)."""
    leads = (
        db.query(Lead)
        .filter(Lead.status == "pending_review")
        .order_by(Lead.found_at.desc())
        .all()
    )
    return leads


@router.get("/stats")
async def get_lead_stats(db: Session = Depends(get_db)):
    """Статистика по лидам для дашборда."""
    total = db.query(Lead).count()
    by_status = {}
    for status_val in ["new", "pending_review", "approved", "letter_sent", "email_sent", "contacted", "no_answer", "closed"]:
        by_status[status_val] = db.query(Lead).filter(Lead.status == status_val).count()

    now = datetime.now(timezone.utc)
    calls_due = db.query(Lead).filter(
        Lead.call_due_at <= now,
        Lead.status.in_(["letter_sent", "email_sent", "approved"]),
    ).count()

    return {
        "total": total,
        "by_status": by_status,
        "calls_due_today": calls_due,
        "pending_review": by_status.get("pending_review", 0),
    }


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Получить один лид по ID."""
    lead = db.query(Lead).filter(Lead.id == str(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}/status")
async def update_status(lead_id: str, body: StatusUpdate, db: Session = Depends(get_db)):
    """Обновить статус лида."""
    lead = db.query(Lead).filter(Lead.id == str(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    valid_statuses = ["new", "pending_review", "approved", "letter_sent", "email_sent", "contacted", "no_answer", "closed"]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    lead.status = body.status
    db.commit()
    return {"id": str(lead.id), "status": lead.status}


@router.patch("/{lead_id}/notes")
async def update_notes(lead_id: str, body: NotesUpdate, db: Session = Depends(get_db)):
    """Добавить/обновить заметку к лиду."""
    lead = db.query(Lead).filter(Lead.id == str(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.notes = body.notes
    db.commit()
    return {"id": str(lead.id), "notes": lead.notes}


@router.post("/{lead_id}/approve")
async def approve_lead(lead_id: str, body: ApproveRequest, db: Session = Depends(get_db)):
    """
    Ручной апрув для Semi-Autonomous лидов.
    Переводит из pending_review → approved и записывает audit trail.
    """
    lead = db.query(Lead).filter(Lead.id == str(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail=f"Lead status is '{lead.status}', expected 'pending_review'"
        )

    now = datetime.now(timezone.utc)
    lead.status = "approved"
    lead.is_approved = True
    lead.approved_by = body.approved_by
    lead.approved_at = now
    lead.approval_reason = body.reason

    # Устанавливаем call_due через 48 часов (после будущей отправки письма)
    lead.call_due_at = now + timedelta(hours=48)

    db.commit()

    return {
        "id": str(lead.id),
        "status": lead.status,
        "approved_by": lead.approved_by,
        "approved_at": lead.approved_at.isoformat(),
    }


@router.post("/{lead_id}/snooze")
async def snooze_lead(lead_id: str, body: SnoozeRequest, db: Session = Depends(get_db)):
    """Перенести звонок на X часов (по умолчанию +24ч)."""
    lead = db.query(Lead).filter(Lead.id == str(lead_id)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.now(timezone.utc)
    lead.call_due_at = now + timedelta(hours=body.hours)
    db.commit()

    return {
        "id": str(lead.id),
        "call_due_at": lead.call_due_at.isoformat(),
    }
