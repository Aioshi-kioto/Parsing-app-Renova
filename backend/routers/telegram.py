"""
Telegram Webhook Router (Aiogram integration)
"""
from fastapi import APIRouter, Request, HTTPException
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands
from aiogram.types import Update

import logging

try:
    from backend.config import settings
    from backend.telegram.bot.middlewares.auth import AuthMiddleware
    from backend.telegram.bot.handlers import handlers, lead_actions
except ImportError:
    from config import settings
    from telegram.bot.middlewares.auth import AuthMiddleware
    from telegram.bot.handlers import handlers, lead_actions

logger = logging.getLogger(__name__)

router = APIRouter()

# Инициализируем Aiogram инстансы
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Настраиваем Middleware защиты
auth_middleware = AuthMiddleware(allowed_chat_id=settings.TELEGRAM_CHAT_ID)
dp.message.middleware(auth_middleware)
dp.callback_query.middleware(auth_middleware)

# Регистрируем роутеры команд
dp.include_router(handlers.router)
dp.include_router(lead_actions.router)

BOT_COMMANDS = [
    BotCommand(command="start", description="Запустить бота"),
    BotCommand(command="help", description="Список команд"),
    BotCommand(command="settings", description="Настройки бота"),
    BotCommand(command="stats", description="Сводка за день"),
    BotCommand(command="pending", description="Лиды на проверке"),
    BotCommand(command="queue", description="Очередь рассылки"),
    BotCommand(command="parsers", description="Управление парсерами"),
    BotCommand(command="demo", description="Демо всех уведомлений"),
]


async def setup_telegram_bot_commands() -> None:
    """
    Publish bot commands to Telegram menu.
    This is required for command list to appear in client UI.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram token is empty, skip set_my_commands")
        return
    try:
        await bot.set_my_commands(BOT_COMMANDS)
        await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Telegram commands published successfully")
    except Exception as e:
        logger.error(f"Failed to publish Telegram commands: {e}")


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Единый Webhook эндпоинт для Telegram, который передает данные в Aiogram Dispatcher."""
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot=bot, update=update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        # Telegram ожидает HTTP 200, иначе будет повторять отправку вебхука. 
        # Ошибки парсинга логируем, но возвращаем 200.
        return {"ok": True}


@router.post("/test")
async def telegram_test():
    """Отправить тестовое сообщение (проверка подключения)."""
    try:
        from backend.services.outbound.telegram_bot import get_telegram_bot
        alert_bot = get_telegram_bot()
        result = await alert_bot.send_test()
        return {"ok": bool(result), "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/send-all-demos")
async def telegram_send_all_demos():
    """
    Отправить по очереди все типы уведомлений в Telegram (демо, БД не нужна).
    Позволяет проверить, как выглядят сообщения в боте.
    """
    from backend.services.outbound.telegram_bot import get_telegram_bot

    alert_bot = get_telegram_bot()
    if not alert_bot.enabled:
        raise HTTPException(
            status_code=503,
            detail="Telegram bot disabled: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set",
        )

    sent = []
    errors = []

    # 1. Тест
    try:
        r = await alert_bot.send_test()
        sent.append("test")
    except Exception as e:
        errors.append({"type": "test", "error": str(e)})

    # 2. Parser start
    try:
        r = await alert_bot.send_parser_start("Seattle Permits (SDCI)", {
            "Range": "2026-03",
            "Class": "Single Family / Duplex",
            "Verify": "True",
        })
        sent.append("parser_start")
    except Exception as e:
        errors.append({"type": "parser_start", "error": str(e)})

    # 3. Parser finish
    try:
        r = await alert_bot.send_parser_finish("Seattle Permits (SDCI)", {
            "Status": "completed",
            "Range": "2026-03",
            "Permits Found": 73,
            "Verified": 73,
            "Owner Builders": 9,
        })
        sent.append("parser_finish")
    except Exception as e:
        errors.append({"type": "parser_finish", "error": str(e)})

    # 4. Error alert
    try:
        r = await alert_bot.send_error_alert(
            "SDCI Parser",
            "Connection timeout to Socrata API after 30s\n  at requests.get(...)",
        )
        sent.append("error_alert")
    except Exception as e:
        errors.append({"type": "error_alert", "error": str(e)})

    # 5. Call reminder
    try:
        r = await alert_bot.send_call_reminder(
            "123 Main St, Seattle WA 98101",
            "sniper",  # test business mapping
            "lead-demo-001",
        )
        sent.append("call_reminder")
    except Exception as e:
        errors.append({"type": "call_reminder", "error": str(e)})

    # Устаревший шаг 6 с поштучными approval requests удален, 
    # так как апрувы перенесены в дашборд (по команде /pending).

    # 7. Daily limit alert
    try:
        r = await alert_bot.send_daily_limit_alert("Lob", 42)
        sent.append("daily_limit_alert")
    except Exception as e:
        errors.append({"type": "daily_limit_alert", "error": str(e)})

    # 8. Anomaly alert
    try:
        r = await alert_bot.send_anomaly_alert(
            "Резкий всплеск пермитов в ZIP 98101: +300% за день.",
        )
        sent.append("anomaly_alert")
    except Exception as e:
        errors.append({"type": "anomaly_alert", "error": str(e)})

    return {
        "ok": len(errors) == 0,
        "sent": sent,
        "errors": errors,
        "message": f"Sent {len(sent)}/7 demo messages to Telegram.",
    }
