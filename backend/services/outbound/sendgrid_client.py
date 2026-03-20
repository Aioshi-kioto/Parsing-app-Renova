# -*- coding: utf-8 -*-
"""
SendGrid API Client — отправка email.
Используется для лидов после Skip Trace (контактный email).
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "hello@renova.contractors")
SENDGRID_FROM_NAME = os.environ.get("SENDGRID_FROM_NAME", "Renova Contractors")


class SendGridClient:
    BASE_URL = "https://api.sendgrid.com/v3"

    def __init__(self, api_key: str = SENDGRID_API_KEY):
        self.api_key = api_key
        self.enabled = bool(self.api_key and self.api_key.strip())

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_plain: str,
        to_name: Optional[str] = None,
        disable_click_tracking: bool = False,
        body_html: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Отправляет письмо. Возвращает (success, message_id или error_message).
        disable_click_tracking=True — отключает переписывание ссылок (ct.sendgrid.net), лучше для cold outreach.
        body_html — опционально; если задан, отправляется multipart (plain + html).
        """
        if not self.enabled:
            logger.info(f"[SENDGRID] Disabled (no API key). Mock send to {to_email}: {subject[:50]}...")
            return True, "mock_sendgrid_id"

        content = [{"type": "text/plain", "value": body_plain}]
        if body_html:
            content.append({"type": "text/html", "value": body_html})

        payload = {
            "personalizations": [{"to": [{"email": to_email, "name": (to_name or to_email)}], "subject": subject}],
            "from": {"email": SENDGRID_FROM_EMAIL, "name": SENDGRID_FROM_NAME},
            "content": content,
        }
        if disable_click_tracking:
            payload["tracking_settings"] = {"click_tracking": {"enable": False}}

        try:
            with httpx.Client(timeout=30) as client:
                r = client.post(
                    f"{self.BASE_URL}/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
        except Exception as e:
            logger.exception("[SENDGRID] Request failed")
            return False, str(e)

        if r.status_code in (200, 202):
            msg_id = r.headers.get("X-Message-Id") or "ok"
            logger.info(f"[SENDGRID] Sent to {to_email} id={msg_id}")
            return True, msg_id
        logger.warning(f"[SENDGRID] {r.status_code} {r.text}")
        return False, r.text
