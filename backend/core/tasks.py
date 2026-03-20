import os
from celery import Celery
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Инициализация Celery
app = Celery("renova_tasks", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Los_Angeles',
    enable_utc=True,
)

app.conf.beat_schedule = {
    "dispatch-scheduled-operations-every-minute": {
        "task": "backend.core.tasks.dispatch_due_scheduled_operations_task",
        "schedule": 60.0,
    },
    "ingest-decodo-usage-hourly": {
        "task": "backend.core.tasks.ingest_decodo_usage_task",
        "schedule": 3600.0,
    },
}


@app.task(bind=True, max_retries=0, name="backend.core.tasks.dispatch_due_scheduled_operations_task")
def dispatch_due_scheduled_operations_task(self, limit: int = 20):
    """Beat task: диспетчеризует due scheduled operations в реальные parser jobs."""
    try:
        from backend.services.scheduled_operations_service import claim_due_operations, dispatch_operation_now
    except ImportError:
        from services.scheduled_operations_service import claim_due_operations, dispatch_operation_now

    op_ids = claim_due_operations(limit=limit)
    dispatched = 0
    failed = 0
    for op_id in op_ids:
        try:
            dispatch_operation_now(op_id)
            dispatched += 1
        except Exception as error:
            logger.error("Scheduled operation dispatch failed for id=%s: %s", op_id, error)
            failed += 1

    return {"claimed": len(op_ids), "dispatched": dispatched, "failed": failed}

@app.task(bind=True, max_retries=1, name="backend.core.tasks.ingest_decodo_usage_task")
def ingest_decodo_usage_task(self):
    """Hourly: pull Decodo traffic stats and log into billing_logs."""
    import os, requests, json
    api_key = os.environ.get("DECODO_API_KEY", "").strip()
    if not api_key:
        return {"skipped": True, "reason": "DECODO_API_KEY not set"}

    try:
        from backend.services.cost_service import log_billing_event
    except ImportError:
        from services.cost_service import log_billing_event

    try:
        resp = requests.post(
            "https://api.decodo.com/api/v2/statistics/traffic",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"granularity": "hour", "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("data") or data.get("results") or []
        total_bytes = sum(e.get("bytes", 0) for e in entries) if entries else 0
        total_mb = round(total_bytes / (1024 * 1024), 4)
        if total_mb > 0:
            cost_per_gb = 8.50
            cost = round(total_mb / 1024 * cost_per_gb, 6)
            log_billing_event("decodo", "proxy_traffic_mb", cost)
        return {"ingested_mb": total_mb}
    except Exception as exc:
        logger.warning("Decodo usage ingestion failed: %s", exc)
        return {"error": str(exc)}


@app.task(bind=True, max_retries=3)
def send_lob_letter_task(self, lead_id: str, lead_data: dict, template_id: str):
    """
    Фоновая задача для отправки письма через Lob API.
    Обновляет статус лида после успешной отправки.
    """
    from services.outbound.lob_client import get_lob_client
    try:
        from database_setup import SessionLocal
        from db_models import Lead
    except ImportError:
        from backend.database_setup import SessionLocal
        from backend.db_models import Lead
        
    client = get_lob_client()
    
    # Конвертируем данные лида в формат Lob to_address
    name = lead_data.get("contact_name") or "Homeowner"
    address_line1 = lead_data.get("address", "")
    city = lead_data.get("city", "")
    state = "WA"  # По умолчанию для MyBuildingPermit
    zipcode = lead_data.get("zip", "")
    
    if not address_line1:
        logger.warning(f"Cannot send Lob letter to Lead {lead_id}: No address.")
        return False
        
    to_address = {
        "name": name,
        "address_line1": address_line1,
        "address_city": city,
        "address_state": state,
        "address_zip": zipcode,
        "address_country": "US"
    }
    
    merge_variables = {
        "lead_name": name,
        "lead_address": address_line1,
        "case_type": lead_data.get("case_type", "Renovation"),
    }
    
    try:
        # Запускаем async код в sync celery task
        loop = asyncio.get_event_loop()
        if loop.is_closed():
             loop = asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
        
        lob_id = loop.run_until_complete(
            client.send_letter(to_address, template_id, merge_variables)
        )
        
        # Обновляем БД
        db = SessionLocal()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                lead.status = "letter_sent"
                # Запишем lob_id в raw_data для трекинга
                if not isinstance(lead.raw_data, dict):
                    lead.raw_data = {}
                lead.raw_data["lob_id"] = lob_id
                lead.raw_data["letter_sent_at"] = datetime.utcnow().isoformat()
                db.commit()
                logger.info(f"Updated Lead {lead_id} status to 'letter_sent'.")
        finally:
            db.close()
            
        return lob_id
        
    except Exception as exc:
        logger.error(f"Lob task failed for {lead_id}: {exc}")
        # Если это лимит (Safety Cap), мы не ретраим.
        if "DAILY_LIMIT_REACHED" in str(exc):
            logger.warning(f"Safety cap reached, skipping retry for Lead {lead_id}.")
            return None
        raise self.retry(exc=exc, countdown=60) # Ретрай через 60 сек


@app.task(bind=True, max_retries=3)
def send_apollo_email_sequence_task(self, lead_id: str, lead_data: dict, sequence_id: str):
    """
    Фоновая задача для добавления лида в email-воронку через Apollo API.
    Обновляет статус лида после успешного добавления.
    """
    from services.outbound.apollo_client import get_apollo_client
    try:
        from database_setup import SessionLocal
        from db_models import Lead
    except ImportError:
        from backend.database_setup import SessionLocal
        from backend.db_models import Lead
        
    client = get_apollo_client()
    
    # Пытаемся взять готовый email
    contact_email = lead_data.get("contact_email")
    person_name = lead_data.get("contact_name")
    
    # 1. Если email нет, можно попытаться найти через search
    loop = asyncio.get_event_loop()
    if loop.is_closed():
         loop = asyncio.new_event_loop()
         asyncio.set_event_loop(loop)
         
    if not contact_email and person_name:
        logger.info(f"Email not found for Lead {lead_id}, trying to search Apollo for {person_name}...")
        # Упрощенно: ищем в локации
        contacts = loop.run_until_complete(client.search_contacts(q_organization_domains="", q_person_name=person_name))
        for c in contacts:
            if c.get("email"):
                contact_email = c["email"]
                logger.info(f"Found email {contact_email} for Lead {lead_id} in Apollo.")
                break
                
    if not contact_email:
        logger.warning(f"Cannot add Lead {lead_id} to Apollo sequence: No email found.")
        return False
        
    try:
        # 2. Добавляем в Sequence
        action_id = loop.run_until_complete(
            client.add_to_sequence(contact_email, sequence_id)
        )
        
        # Обновляем БД
        db = SessionLocal()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                # Если уже letter_sent, можем оставить его или обновить на complex status
                if lead.status not in ["letter_sent", "email_sent", "contacted"]:
                    lead.status = "email_sent"
                
                if not isinstance(lead.raw_data, dict):
                    lead.raw_data = {}
                lead.raw_data["apollo_action_id"] = action_id
                lead.raw_data["sequence_added_at"] = datetime.utcnow().isoformat()
                lead.raw_data["contact_email"] = contact_email
                lead.contact_email = contact_email # Update main model
                db.commit()
                logger.info(f"Updated Lead {lead_id} with Apollo sequence data.")
        finally:
            db.close()
            
        return action_id
        
    except Exception as exc:
        logger.error(f"Apollo task failed for {lead_id}: {exc}")
        if "LIMIT_REACHED" in str(exc):
            logger.warning(f"Safety cap reached, skipping retry for Lead {lead_id}.")
            return None
        raise self.retry(exc=exc, countdown=60)
