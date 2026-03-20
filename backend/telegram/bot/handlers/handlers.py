from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("help"))
async def help_command(message: Message):
    text = (
        "<pre>RENOVA BOT\n"
        "---\n"
        "Commands:\n"
        "  /start   - Welcome\n"
        "  /stats   - Daily summary\n"
        "  /pending - Leads awaiting approval\n"
        "  /queue   - Outbound queue\n"
        "  /parsers - Parser controls\n"
        "  /demo    - Send all notification templates\n"
        "  /settings - Bot settings\n"
        "</pre>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("settings"))
async def settings_command(message: Message):
    text = (
        "<pre>SETTINGS\n"
        "---\n"
        "Menu: Bot API setMyCommands.\n"
        "Buttons use FRONTEND_URL from .env.\n"
        "Restart bot after .env changes.\n"
        "</pre>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("demo"))
async def demo_command(message: Message):
    try:
        from backend.services.outbound.telegram_bot import get_telegram_bot
    except ImportError:
        from services.outbound.telegram_bot import get_telegram_bot
    bot_service = get_telegram_bot()
    await message.answer("<pre>DEMO\n---\nSending all notification types.</pre>", parse_mode="HTML")
    await bot_service.send_parser_start("Seattle Permits (SDCI)", {"Range": "2026-03", "Class": "Single Family"})
    await bot_service.send_parser_finish("Seattle Permits (SDCI)", {"Permits Found": 42, "Owner Builders": 5})
    await bot_service.send_error_alert("SDCI Parser", "Connection timeout to Socrata API after 30s")
    await bot_service.send_call_reminder("123 Main St, Seattle WA", "sniper", "L-001")
    await bot_service.send_daily_limit_alert("Lob", 15)
    await bot_service.send_anomaly_alert("Spike in ZIP 98101: +300% per day.")
    await message.answer("<pre>DEMO COMPLETE\n---\nAll templates sent.</pre>", parse_mode="HTML")
