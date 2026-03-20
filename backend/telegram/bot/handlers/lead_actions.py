from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.orm import Session
from datetime import datetime
import json

try:
    from backend.database_setup import SessionLocal
    from backend.db_models import Lead
except ImportError:
    from database_setup import SessionLocal
    from db_models import Lead

router = Router()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "<pre>RENOVA BOT\n"
        "---\n"
        "Chat ID authorized. Commands:\n"
        "  /stats   - Daily summary\n"
        "  /pending - Leads awaiting approval\n"
        "  /queue   - Outbound queue status\n"
        "  /parsers - Parser controls (Beta)\n"
        "</pre>"
    )
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/stats"), KeyboardButton(text="/pending")],
            [KeyboardButton(text="/queue"), KeyboardButton(text="/demo")],
            [KeyboardButton(text="/help"), KeyboardButton(text="/settings")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Command or /help",
    )
    await message.answer(text, parse_mode="HTML", reply_markup=reply_kb)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Сводка за день по лидам."""
    db: Session = next(get_db())
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total = db.query(Lead).filter(Lead.found_at >= today_start).count()
    red = db.query(Lead).filter(Lead.found_at >= today_start, Lead.priority == "RED").count()
    yellow = db.query(Lead).filter(Lead.found_at >= today_start, Lead.priority == "YELLOW").count()
    green = db.query(Lead).filter(Lead.found_at >= today_start, Lead.priority == "GREEN").count()
    
    pending = db.query(Lead).filter(Lead.status == "pending_review").count()
    
    text = (
        f"<pre>STATS (TODAY UTC)\n"
        f"---\n"
        f"TOTAL:   {total}\n"
        f"RED:     {red}\n"
        f"YELLOW:  {yellow}\n"
        f"GREEN:   {green}\n"
        f"---\n"
        f"PENDING APPROVAL: {pending} (see /pending)\n"
        f"</pre>"
    )
    try:
        from backend.config import settings
    except ImportError:
        from config import settings
    frontend_url = getattr(settings, "FRONTEND_URL", "https://google.com")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="DASHBOARD", url=f"{frontend_url}/")]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.message(Command("pending"))
async def cmd_pending(message: Message):
    """Показать количество ожидающих апрува лидов и дать ссылку на дашборд."""
    db: Session = next(get_db())
    pending_count = db.query(Lead).filter(Lead.status == "pending_review").count()
    
    if pending_count == 0:
        await message.answer("<pre>PENDING\n---\nNo leads awaiting approval.</pre>", parse_mode="HTML")
        return
    text = (
        f"<pre>PENDING APPROVAL\n"
        f"---\n"
        f"IN QUEUE: {pending_count} leads\n"
        f"---\n"
        f"Open dashboard to review.</pre>"
    )
    try:
        from backend.config import settings
    except ImportError:
        from config import settings
    frontend_url = getattr(settings, "FRONTEND_URL", "https://google.com")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="DASHBOARD", url=f"{frontend_url}/")]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.message(Command("queue"))
async def cmd_queue(message: Message):
    """Показать состояние очереди на рассылку (Lob/Apollo)."""
    db: Session = next(get_db())
    
    # Лиды, которые готовы к отправке Lob
    # SQL logic for Sprint 3.8
    # Status 'new' or 'approved', but not 'letter_sent'
    in_queue = db.query(Lead).filter(
        Lead.status.in_(["new", "approved"]),
        Lead.sent_lob_at.is_(None)
    ).count()
    
    red_q = db.query(Lead).filter(Lead.status.in_(["new", "approved"]), Lead.sent_lob_at.is_(None), Lead.priority == "RED").count()
    yellow_q = db.query(Lead).filter(Lead.status.in_(["new", "approved"]), Lead.sent_lob_at.is_(None), Lead.priority == "YELLOW").count()
    green_q = db.query(Lead).filter(Lead.status.in_(["new", "approved"]), Lead.sent_lob_at.is_(None), Lead.priority == "GREEN").count()
    
    text = (
        f"<pre>QUEUE (08:00 AM PST)\n"
        f"---\n"
        f"LOB:     {in_queue}/50\n"
        f"---\n"
        f"RED:    {red_q}\n"
        f"YELLOW: {yellow_q}\n"
        f"GREEN:  {green_q}\n"
        f"---\n"
        f"GREEN deferred if RED+YELLOW > 50.</pre>"
    )
    try:
        from backend.config import settings
    except ImportError:
        from config import settings
    frontend_url = getattr(settings, "FRONTEND_URL", "https://google.com")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="DASHBOARD", url=f"{frontend_url}/")]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.message(Command("parsers"))
async def cmd_parsers(message: Message):
    text = "<pre>PARSERS\n---\nSelect parser to run:</pre>"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="SDCI", callback_data="run_parser:sdci"),
            InlineKeyboardButton(text="MBP", callback_data="run_parser:mbp"),
        ]
    ])
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("run_parser:"))
async def handle_run_parser(callback: CallbackQuery):
    _, parser_name = callback.data.split(":")
    await callback.answer(f"Run {parser_name.upper()} requested (in development).", show_alert=True)
