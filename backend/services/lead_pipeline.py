"""
Lead Pipeline service.

Связывает существующие парсеры с Sprint 1 CRM-слоем:
record -> Rules Engine -> leads (SQLAlchemy) -> optional Telegram approval alert.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    # Когда модуль импортируется как часть пакета backend.*
    from backend.database_setup import SessionLocal
    from backend.db_models import Lead
    from backend.services.rules_engine import classify_lead
    from backend.services.outbound.telegram_bot import get_telegram_bot
except ImportError:
    # Локальный запуск из директории backend
    from database_setup import SessionLocal
    from db_models import Lead
    from services.rules_engine import classify_lead
    from services.outbound.telegram_bot import get_telegram_bot

logger = logging.getLogger(__name__)


def _to_jsonable(data: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort conversion to JSON-serializable dict."""
    out: Dict[str, Any] = {}
    for k, v in data.items():
        try:
            if isinstance(v, (str, int, float, bool)) or v is None:
                out[k] = v
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            else:
                out[k] = str(v)
        except Exception:
            out[k] = str(v)
    return out


def _run_async_safely(coro):
    """Run async coroutine from sync context (works in/without running loop)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def ingest_record_to_leads(record: Dict[str, Any], source: str) -> List[str]:
    """
    Классифицирует запись и upsert-ит лиды.

    Returns:
        list[str]: созданные/обновлённые case_type.
    """
    matches = classify_lead(record, source)
    if not matches:
        return []

    address = (record.get("address") or "").strip()
    if not address:
        return []

    city = (record.get("city") or "").strip() or None
    zip_code = (record.get("zip") or record.get("zipcode") or "").strip() or None
    contact_name = (record.get("applicant_name") or record.get("owner_name") or record.get("contact_name") or "").strip() or None
    contact_email = (record.get("contact_email") or "").strip() or None
    contact_phone = (record.get("applicant_phone") or record.get("contact_phone") or "").strip() or None
    raw_data = _to_jsonable(record)

    db = SessionLocal()
    touched: List[str] = []
    try:
        permit_number = (record.get("permit_number") or record.get("permit_num") or "").strip() or None

        for m in matches:
            # Дедупликация: ищем по permit_number ИЛИ (по адресу и типу кейса)
            query = db.query(Lead).filter(Lead.source == source)
            
            if permit_number:
                # В PostgreSQL JSONB можно искать так, но кросс-БД вариант сложнее.
                # Поэтому мы делаем гибридный поиск + фильтруем в Python, чтобы не заморачиваться с диалектами
                candidates = query.filter(
                    Lead.address == address,
                    Lead.case_type == m.case_type
                ).all()
                # Или просто ищем все лиды по адресу и проверяем raw_data
                existing = None
                for c in candidates:
                    raw_pnum = c.raw_data.get("permit_number") or c.raw_data.get("permit_num")
                    if raw_pnum == permit_number or (c.address == address and c.case_type == m.case_type):
                        existing = c
                        break
            else:
                existing = (
                    query.filter(
                        Lead.address == address,
                        Lead.case_type == m.case_type,
                    )
                    .order_by(Lead.found_at.desc())
                    .first()
                )

            if existing:
                existing.priority = m.priority
                existing.raw_data = raw_data
                existing.contact_name = contact_name or existing.contact_name
                existing.contact_email = contact_email or existing.contact_email
                existing.contact_phone = contact_phone or existing.contact_phone
                existing.matched_cases = sorted(set((existing.matched_cases or []) + [m.case_type]))
                if existing.status in (None, "", "new"):
                    existing.status = m.initial_status
                touched.append(m.case_type)
                continue

            lead = Lead(
                address=address,
                city=city,
                zip=zip_code,
                case_type=m.case_type,
                priority=m.priority,
                source=source,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                status=m.initial_status,
                is_approved=False,
                raw_data=raw_data,
                matched_cases=[m.case_type],
                found_at=datetime.utcnow(),
            )
            db.add(lead)
            db.flush()  # to get lead.id before commit for alerts

            if m.initial_status == "pending_review":
                # В Спринте 3.7+ мы больше не отправляем индивидуальные алерты 
                # для каждого `pending_review` лида (чтобы избежать спама из 100+ сообщений).
                # Лид сохраняется в БД, а пользователь увидит их через команду /pending в Telegram.
                pass
            elif m.initial_status == "new":
                # В Спринте 3.8 автономная отправка для GREEN/YELLOW кейсов 
                # больше не происходит мгновенно. Лид остается в БД со статусом "new",
                # и его подхватит Outbound Scheduler (backend/services/outbound_scheduler.py)
                # во время ежедневной утренней рассылки (08:00 AM PST).
                pass

            touched.append(m.case_type)

        db.commit()
        return touched
    except Exception as e:
        db.rollback()
        logger.warning("Lead ingestion skipped due to DB error: %s", e)
        return []
    finally:
        db.close()
