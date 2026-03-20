"""
Apollo.io API Client for Email Sequences.
Поиск email-контактов по имени/адресу и добавление их в Sequence (воронку).
С поддержкой Safety Caps (лимиты вызовов в день).
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx
import redis.asyncio as aioredis # type: ignore

logger = logging.getLogger(__name__)

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Safety Caps: лимит на кол-во найденных контактов / добавленных в sequence
APOLLO_DAILY_LIMIT = int(os.environ.get("APOLLO_DAILY_LIMIT", "100"))

class ApolloClient:
    """Клиент для Apollo.io API (v1)."""
    
    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self, api_key: str = APOLLO_API_KEY):
        self.api_key = api_key
        self.enabled = bool(self.api_key)
        self.redis = aioredis.from_url(REDIS_URL, decode_responses=True)

    async def _check_daily_limit(self) -> bool:
        """Проверяет дневной лимит обращений к Apollo (добавление в Sequence)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"apollo_sent_count_{today}"
        
        count = await self.redis.get(key)
        if count and int(count) >= APOLLO_DAILY_LIMIT:
            logger.warning(f"[APOLLO] Daily limit ({APOLLO_DAILY_LIMIT}) reached for today ({today}).")
            return False
            
        return True

    async def _increment_daily_limit(self):
        """Увеличивает счетчик обращений на сегодня."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"apollo_sent_count_{today}"
        
        await self.redis.incr(key)
        await self.redis.expire(key, 86400 * 2)

    async def search_contacts(self, q_organization_domains: str, q_person_name: str) -> List[Dict]:
        """
        Ищет контакты в Apollo по домену компании или имени человека.
        (Часто для B2C сложнее, Apollo лучше для B2B, но мы ищем по имени и локации).
        """
        if not self.enabled:
            logger.info(f"[APOLLO] Disabled. Mock search for: {q_person_name}")
            return [{"id": "mock_contact_id", "email": "mock@example.com"}]

        url = f"{self.BASE_URL}/mixed_people/search"
        payload = {
            "api_key": self.api_key,
            "q_organization_domains": q_organization_domains,
            "q_person_name": q_person_name,
        }
        
        # Запрос в Apollo не считаем за отправку (не инкрементируем счетчик лимитов), 
        # но стоит следить за API Credit Limit
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("people", [])
        except Exception as e:
            logger.error(f"[APOLLO] Error searching contacts: {e}")
            return []

    async def add_to_sequence(self, contact_email: str, sequence_id: str) -> Optional[str]:
        """
        Добавляет уже существующий email в Sequence (Campaign) в Apollo.
        """
        if not self.enabled:
            logger.info(f"[APOLLO] Disabled. Mock add {contact_email} to sequence {sequence_id}")
            return "mock_action_id"

        can_send = await self._check_daily_limit()
        if not can_send:
            raise Exception("APOLLO_DAILY_LIMIT_REACHED")

        # Apollo API v1 - добавление в sequence
        url = f"{self.BASE_URL}/emailer_campaigns/{sequence_id}/add_contact_ids"
        
        payload = {
            "api_key": self.api_key,
            "contact_emails": [contact_email]
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                await self._increment_daily_limit()
                
                return "added_to_sequence"
                
        except Exception as e:
            logger.error(f"[APOLLO] Error adding to sequence: {e}")
            raise


_apollo_client = None

def get_apollo_client() -> ApolloClient:
    global _apollo_client
    if _apollo_client is None:
        _apollo_client = ApolloClient()
    return _apollo_client
