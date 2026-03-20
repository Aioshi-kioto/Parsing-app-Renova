import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import Session

# Fallback imports
try:
    from backend.database_setup import SessionLocal
    from backend.db_models import Lead
    from backend.services.outbound.telegram_bot import get_telegram_bot
except ImportError:
    from database_setup import SessionLocal
    from db_models import Lead
    from services.outbound.telegram_bot import get_telegram_bot

logger = logging.getLogger(__name__)

LOB_DAILY_LIMIT = 50
APOLLO_DAILY_LIMIT = 100
PST_TZ = pytz.timezone('America/Los_Angeles')


def get_current_pst() -> datetime:
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(PST_TZ)


async def send_daily_queue_summary(db: Session, sent_lob: int, lob_limit: int):
    """Отправляем утренний отчет об очереди."""
    bot = get_telegram_bot()
    
    in_queue = db.query(Lead).filter(
        Lead.status.in_(["new", "approved"]),
        Lead.sent_lob_at.is_(None)
    ).count()
    
    text = (
        f"<pre>DAILY OUTBOUND COMPLETE (PST)\n"
        f"---\n"
        f"LOB SENT:  {sent_lob}/{lob_limit}\n"
        f"IN QUEUE: {in_queue} leads\n"
    )
    red_q = db.query(Lead).filter(Lead.status.in_(["new", "approved"]), Lead.sent_lob_at.is_(None), Lead.priority == "RED").count()
    if red_q > 0:
        text += f"---\nWARNING: {red_q} RED leads still in queue (daily limit reached).\n"
    text += "</pre>"
    await bot.send_message(text)


def is_duplicate_address(db: Session, address: str, days: int = 90) -> bool:
    """Проверка, было ли отправлено письмо на этот адрес в последние N дней."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    count = db.query(Lead).filter(
        Lead.address == address,
        Lead.sent_lob_at >= cutoff
    ).count()
    return count > 0


async def prune_stale_pending_leads(db: Session):
    """Auto-reject для лидов, ожидающих ручного апрува более 48 часов."""
    cutoff = datetime.utcnow() - timedelta(hours=48)
    stale_leads = db.query(Lead).filter(
        Lead.status == "pending_review",
        Lead.found_at <= cutoff
    ).all()
    
    if stale_leads:
        bot = get_telegram_bot()
        for lead in stale_leads:
            lead.status = "auto_rejected"
            lead.notes = (lead.notes or "") + "\nАвтоматически отклонено: истекло 48 часов ожидания."
            
            safe_addr = bot.escape_html(lead.address)
            await bot.send_message(
                f"<pre>LEAD AUTO-REJECTED\n"
                f"ID:      {lead.id}\n"
                f"ADDRESS: {safe_addr}\n"
                f"---\n"
                f"No Approve within 48h.</pre>"
            )
        
        db.commit()


async def run_daily_outbound_sweep():
    """Ежедневная задача для отправки писем через Lob и Apollo"""
    logger.info("Starting Daily Outbound Sweep (08:00 AM PST)")
    
    db = SessionLocal()
    try:
        # 1. Сначала отклоняем протухшие лиды
        await prune_stale_pending_leads(db)
        
        # 2. Выбираем лиды для отправки с сортировкой по приоритету
        # RED (1) -> YELLOW (2) -> GREEN (3), затем по времени нахождения
        query = db.query(Lead).filter(
            Lead.status.in_(["new", "approved"]),
            Lead.sent_lob_at.is_(None)
        ).order_by(
            Lead.priority.asc(), # Временно так, но лучше использовать CASE
        )
        # SQLAlchemy CASE sorting для RED/YELLOW/GREEN
        from sqlalchemy import case
        priority_sort = case(
            (Lead.priority == 'RED', 1),
            (Lead.priority == 'YELLOW', 2),
            (Lead.priority == 'GREEN', 3),
            else_=4
        )
        
        leads_to_process = db.query(Lead).filter(
            Lead.status.in_(["new", "approved"]),
            Lead.sent_lob_at.is_(None)
        ).order_by(
            priority_sort.asc(),
            Lead.found_at.asc()
        ).limit(LOB_DAILY_LIMIT).all()
        
        sent_count = 0
        
        for lead in leads_to_process:
            # 3. Защита от спама (Дедупликация)
            if is_duplicate_address(db, lead.address, days=90):
                lead.status = "skipped_duplicate"
                lead.notes = (lead.notes or "") + "\nSkipped: Письмо на этот адрес уже уходило в течение 90 дней."
                continue
                
            # 4. Отправка в Celery (Lob API)
            try:
                from backend.core.tasks import send_lob_letter_task
            except ImportError:
                from core.tasks import send_lob_letter_task

            template_id = "tmpl_123456789" # Этот шаблон будет заменен на реальный
            lead_data = {
                "contact_name": lead.contact_name,
                "address": lead.address,
                "city": lead.city,
                "zip": lead.zip,
                "case_type": lead.case_type,
            }
            
            try:
                send_lob_letter_task.delay(
                    lead_id=str(lead.id),
                    lead_data=lead_data,
                    template_id=template_id
                )
                # Помечаем что письмо встало в очередь Lob
                lead.sent_lob_at = datetime.utcnow()
                lead.status = "letter_sent"
                
                # Планируем звонок (через 3 дня для RED, 7 дней для остальных)
                call_delay = 3 if lead.priority == "RED" else 7
                lead.call_due_at = datetime.utcnow() + timedelta(days=call_delay)
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to queue Lob task for lead {lead.id}: {e}")
                
        db.commit()
        
        # 5. Уведомление в Telegram об итогах Sweep
        await send_daily_queue_summary(db, sent_count, LOB_DAILY_LIMIT)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Critical error during outbound sweep: {e}")
        bot = get_telegram_bot()
        await bot.send_error_alert("OutboundScheduler", str(e))
    finally:
        db.close()


async def scheduler_loop():
    """Фоновый цикл для запуска Sweep ровно в 08:00 AM PST"""
    logger.info("Outbound Scheduler Loop Started.")
    while True:
        now_pst = get_current_pst()
        
        # Если сейчас 8 утра PST (с погрешностью в 1 минуту)
        if now_pst.hour == 8 and now_pst.minute == 0:
            # Проверяем, не выходной ли сегодня (Lob не печатает по выходным)
            if now_pst.weekday() < 5:  # 0-4 это Пн-Пт
                await run_daily_outbound_sweep()
            else:
                logger.info(f"Skipping Lob Sweep because it's weekend (PST): {now_pst.strftime('%A')}")
            
            # Ждем час, чтобы не запустить повторно в ту же минуту
            await asyncio.sleep(3600)
        
        # Проверяем каждую минуту
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(scheduler_loop())
