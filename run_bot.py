"""
Script to run Telegram Bot in Long Polling mode for local testing.
This bypasses the webhook setup and allows testing commands directly from your machine.
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands
from backend.config import settings
from backend.telegram.bot.handlers import handlers, lead_actions
from backend.telegram.bot.middlewares.auth import AuthMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def main():
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
        return

    print("Starting Telegram Bot in LONG POLLING mode...")
    print(f"Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"Allowed Chat ID: {settings.TELEGRAM_CHAT_ID}")

    # Initialize Bot and Dispatcher
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Setup Middleware
    auth_middleware = AuthMiddleware(allowed_chat_id=settings.TELEGRAM_CHAT_ID)
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(auth_middleware)

    # Include Routers
    dp.include_router(handlers.router)
    dp.include_router(lead_actions.router)

    # Publish commands to Telegram menu so users see "/" command list.
    try:
        await bot.set_my_commands(BOT_COMMANDS)
        await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Telegram commands published successfully")
    except Exception as e:
        logger.warning(f"Failed to publish Telegram commands: {e}")

    # Start Polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
