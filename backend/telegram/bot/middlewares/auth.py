import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    """
    Middleware for checking if the incoming request is from an allowed chat ID.
    If the effective chat ID doesn't match the required TELEGRAM_CHAT_ID,
    the update is silently ignored (security best practice).
    """
    def __init__(self, allowed_chat_id: str):
        self.allowed_chat_id = str(allowed_chat_id)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        chat_id = None
        
        if isinstance(event, Message):
            chat_id = str(event.chat.id)
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = str(event.message.chat.id)
            
        if chat_id and chat_id != self.allowed_chat_id:
            logger.warning(f"Blocked unauthorized access attempt from chat_id: {chat_id}")
            # Silently drop the update
            return None
            
        return await handler(event, data)
