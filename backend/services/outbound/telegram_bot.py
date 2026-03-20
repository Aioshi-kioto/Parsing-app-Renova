"""
Telegram adapter for backend services.

Actual message logic lives in `backend/telegram/bot/services/alerts_service.py`.
This module keeps backward-compatible imports for routers/parsers.
"""

from __future__ import annotations

from typing import Optional

try:
    from backend.config import settings
except Exception:
    from config import settings

try:
    from backend.telegram.bot.services.alerts_service import TelegramAlertsService
except Exception:
    # Local run from backend/ as cwd (without package prefix)
    from telegram.bot.services.alerts_service import TelegramAlertsService


TelegramBot = TelegramAlertsService

_bot_instance: Optional[TelegramBot] = None


def get_telegram_bot() -> TelegramBot:
    """Get singleton telegram bot adapter."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot(
            token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
        )
    return _bot_instance


async def send_alert(message: str) -> Optional[dict]:
    """Module-level shortcut: send a plain-text Telegram alert."""
    bot = get_telegram_bot()
    safe = TelegramAlertsService.escape_html(message)
    return await bot.send_message(f"<pre>{safe}</pre>")


async def send_job_started(job_type: str, job_id) -> Optional[dict]:
    bot = get_telegram_bot()
    safe_type = TelegramAlertsService.escape_html(job_type)
    text = f"<pre>JOB STARTED\nTYPE: {safe_type}\nID:   #{job_id}\n---\nScanning...</pre>"
    return await bot.send_message(text)


async def send_job_completed(job_type: str, job_id, stats: dict) -> Optional[dict]:
    bot = get_telegram_bot()
    safe_type = TelegramAlertsService.escape_html(job_type)
    records = stats.get("records", 0)
    leads = stats.get("leads", 0)
    text = f"<pre>JOB COMPLETED\nTYPE:    {safe_type}\nID:      #{job_id}\n---\nRECORDS: {records}\nLEADS:   {leads}</pre>"
    return await bot.send_message(text)


async def send_outbound_batch_report(stats: dict) -> Optional[dict]:
    bot = get_telegram_bot()
    letters = stats.get("letters", 0)
    emails = stats.get("emails", 0)
    text = f"<pre>OUTBOUND BATCH\n---\nLETTERS (LOB):   {letters}\nEMAILS (APOLLO): {emails}</pre>"
    return await bot.send_message(text)


async def send_error_alert_simple(job_type: str, error: str) -> Optional[dict]:
    bot = get_telegram_bot()
    safe = TelegramAlertsService.escape_html(str(error)[:500])
    text = f"<pre>ERROR\nJOB: {TelegramAlertsService.escape_html(job_type)}\n---\n{safe}</pre>"
    return await bot.send_message(text)

