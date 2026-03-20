"""
Lob API Client for Direct Mail.
Отправка физических писем с учетом Safety Caps (лимиты отправки в день).
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
import redis.asyncio as aioredis # type: ignore

logger = logging.getLogger(__name__)

# Получение настроек
LOB_API_KEY = os.environ.get("LOB_API_KEY")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Лимит писем в день (Safety Cap)
LOB_DAILY_LIMIT = int(os.environ.get("LOB_DAILY_LIMIT", "50"))

class LobClient:
    """Клиент для работы с Lob API."""
    
    BASE_URL = "https://api.lob.com/v1"
    
    def __init__(self, api_key: str = LOB_API_KEY):
        self.api_key = api_key
        self.enabled = bool(self.api_key)
        self.redis = aioredis.from_url(REDIS_URL, decode_responses=True)

    async def _check_daily_limit(self) -> bool:
        """Проверяет дневной лимит отправки писем в Redis (Safety Cap)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"lob_sent_count_{today}"
        
        count = await self.redis.get(key)
        if count and int(count) >= LOB_DAILY_LIMIT:
            logger.warning(f"[LOB] Daily limit ({LOB_DAILY_LIMIT}) reached for today ({today}).")
            return False
            
        return True

    async def _increment_daily_limit(self):
        """Увеличивает счетчик писем на сегодня."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"lob_sent_count_{today}"
        
        await self.redis.incr(key)
        await self.redis.expire(key, 86400 * 2)  # храним 2 дня для надежности

    async def send_letter(self, to_address: Dict[str, Any], template_id: str, merge_variables: Dict[str, Any]) -> Optional[str]:
        """
        Отправляет физическое письмо (Letter) через Lob API.
        to_address: dict с полями name, address_line1, address_city, address_state, address_zip
        template_id: ID шаблона письма в Lob (tmpl_...)
        """
        if not self.enabled:
            logger.info(f"[LOB] Disabled (no API key). Mock send to: {to_address.get('name')} at {to_address.get('address_line1')} using {template_id}")
            return "mock_lob_id_12345"

        # 1. Проверка Safety Caps
        can_send = await self._check_daily_limit()
        if not can_send:
            # Alerting (можно пробросить в Telegram позже через Exception)
            raise Exception("LOB_DAILY_LIMIT_REACHED")

        # 2. Формирование запроса к Lob API
        url = f"{self.BASE_URL}/letters"
        
        payload = {
            "description": f"Lead mailer for {to_address.get('name')}",
            "to": to_address,
            # От кого отправляем (from). Можно зашить ID готового адреса в Lob.
            # Для демо используем заглушку, но в проде нужно использовать реальный from address ID
            "from": {
                "name": "Renova Group",
                "address_line1": "123 Main St",
                "address_city": "Seattle",
                "address_state": "WA",
                "address_zip": "98101",
                "address_country": "US"
            },
            "file": template_id,
            "merge_variables": merge_variables,
            "color": True,
            "use_type": "marketing"
        }

        # 3. Отправка
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url, 
                    json=payload, 
                    auth=(self.api_key, "")  # Lob использует HTTP Basic Auth, пароль пустой
                )
                response.raise_for_status()
                data = response.json()
                
                # 4. Увеличиваем счетчик после успешной отправки
                await self._increment_daily_limit()
                logger.info(f"[LOB] Letter sent successfully. ID: {data.get('id')}")
                
                return data.get("id")
                
        except httpx.HTTPStatusError as e:
            from .lob_errors import parse_lob_error, format_lob_error_for_log
            parsed = parse_lob_error(e.response.text, e.response.status_code)
            logger.error("[LOB] %s", format_lob_error_for_log(parsed))
            raise Exception(f"Lob API error: {parsed.get('status_code')} | {parsed.get('message', '')[:100]}")
        except Exception as e:
            logger.error(f"[LOB] Error sending letter: {e}")
            raise

_lob_client = None

def get_lob_client() -> LobClient:
    global _lob_client
    if _lob_client is None:
        _lob_client = LobClient()
    return _lob_client
