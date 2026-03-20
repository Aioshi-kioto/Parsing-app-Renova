from __future__ import annotations

import html
from typing import Optional

import httpx


class TelegramAlertsService:
    """Unified Telegram notification service used by backend parsers/pipeline."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML symbols for Telegram API to avoid parsing errors."""
        if not isinstance(text, str):
            text = str(text)
        return html.escape(text)

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None,
    ) -> Optional[dict]:
        if not self.enabled:
            return None

        url = f"{self.BASE_URL.format(token=self.token)}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> Optional[dict]:
        if not self.enabled:
            return None

        url = f"{self.BASE_URL.format(token=self.token)}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> Optional[dict]:
        if not self.enabled:
            return None
        url = f"{self.BASE_URL.format(token=self.token)}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id, "text": text}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    CASE_NAMES = {
        "sniper": "PERMIT_SNIPER",
        "heloc_no_permit": "HELOC_NO_PERMIT",
        "permit_no_contractor": "PERMIT_NO_CONTRACTOR",
        "code_violation": "CODE_VIOLATION",
        "sold_with_permit": "SOLD_WITH_PERMIT",
    }

    def _get_case_name(self, case_type: str) -> str:
        if not case_type:
            return "UNKNOWN"
        return self.CASE_NAMES.get(case_type.lower(), case_type.upper())

    async def send_call_reminder(self, lead_address: str, lead_case: str, lead_id: str) -> Optional[dict]:
        safe_addr = self.escape_html(lead_address)
        human_case = self.escape_html(self._get_case_name(lead_case))
        text = (
            f"<pre>"
            f"CALL REMINDER\n"
            f"ADDRESS:  {safe_addr}\n"
            f"CASE:     {human_case}\n"
            f"ID:       {lead_id}\n"
            f"---\n"
            f"Letter delivered 3 days ago. Follow-up call or visit recommended.\n"
            f"</pre>"
        )
        try:
            from backend.config import settings
        except ImportError:
            from config import settings
        frontend_url = getattr(settings, "FRONTEND_URL", "https://google.com")
        reply_markup = {"inline_keyboard": [[{"text": "DASHBOARD", "url": f"{frontend_url}/"}]]}
        return await self.send_message(text, reply_markup=reply_markup)

    async def send_daily_limit_alert(self, channel: str, queue_size: int) -> Optional[dict]:
        safe_channel = self.escape_html(channel)
        text = (
            f"<pre>"
            f"DAILY OUTBOUND COMPLETE\n"
            f"CHANNEL:  {safe_channel}\n"
            f"IN QUEUE: {queue_size} leads\n"
            f"---\n"
            f"Resume at 08:00 AM PST.\n"
            f"</pre>"
        )
        try:
            from backend.config import settings
        except ImportError:
            from config import settings
        frontend_url = getattr(settings, "FRONTEND_URL", "https://google.com")
        reply_markup = {"inline_keyboard": [[{"text": "DASHBOARD", "url": f"{frontend_url}/"}]]}
        return await self.send_message(text, reply_markup=reply_markup)

    async def send_anomaly_alert(self, message: str) -> Optional[dict]:
        safe = self.escape_html(message)
        return await self.send_message(f"<pre>ANOMALY\n---\n{safe}\n\nRequires analyst review.</pre>")

    async def send_error_alert(self, service: str, error_msg: str) -> Optional[dict]:
        safe_service = self.escape_html(service)
        short_err = str(error_msg)[:600] + ("..." if len(str(error_msg)) > 600 else "")
        safe_err = self.escape_html(short_err)
        text = (
            f"<pre>ERROR\n"
            f"SERVICE: {safe_service}\n"
            f"---\n"
            f"{safe_err}\n"
            f"---\n"
            f"Retry scheduled. Forward to support if persistent.</pre>"
        )
        return await self.send_message(text)

    async def send_parser_start(self, parser_name: str, options: dict) -> Optional[dict]:
        safe_name = self.escape_html(parser_name)
        params_str = "\n".join([f"  {self.escape_html(k)}: {self.escape_html(str(v))}" for k, v in options.items()])
        text = (
            f"<pre>JOB STARTED\n"
            f"PARSER: {safe_name}\n"
            f"---\n"
            f"{params_str}\n"
            f"---\n"
            f"Running. Completion notice will follow.</pre>"
        )
        return await self.send_message(text)

    async def send_parser_finish(self, parser_name: str, stats: dict) -> Optional[dict]:
        safe_name = self.escape_html(parser_name)
        found = stats.get("Permits Found", stats.get("total_permits", 0))
        owner_builders = stats.get("Owner Builders", stats.get("owner_builders_found", 0))
        text = (
            f"<pre>JOB COMPLETED\n"
            f"PARSER: {safe_name}\n"
            f"---\n"
            f"RECORDS:        {found}\n"
            f"OWNER_BUILDERS: {owner_builders}\n"
            f"---\n"
            f"Leads sorted. RED queued for letters. Check /stats.</pre>"
        )
        try:
            from backend.config import settings
        except ImportError:
            from config import settings
        frontend_url = getattr(settings, "FRONTEND_URL", "https://google.com")
        reply_markup = {"inline_keyboard": [[{"text": "DASHBOARD", "url": f"{frontend_url}/"}]]}
        return await self.send_message(text, reply_markup=reply_markup)

    async def send_test(self) -> Optional[dict]:
        return await self.send_message("<pre>RENOVA BOT\n---\nConnected. Ready for commands.</pre>")

