# -*- coding: utf-8 -*-
"""
Twilio API Client — отправка SMS.
Номер получателя из BatchData Skip Trace.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")


class TwilioClient:
    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(
        self,
        account_sid: str = TWILIO_ACCOUNT_SID,
        auth_token: str = TWILIO_AUTH_TOKEN,
        from_number: str = TWILIO_PHONE_NUMBER,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = (from_number or "").strip()
        self.enabled = bool(self.account_sid and self.auth_token and self.from_number)

    def send_sms(self, to_phone: str, body: str) -> tuple[bool, Optional[str]]:
        """
        Отправляет SMS. to_phone в формате E.164 (например +12065551234).
        Возвращает (success, message_sid или error_message).
        """
        if not self.enabled:
            logger.info(f"[TWILIO] Disabled (missing env). Mock SMS to {to_phone}: {body[:50]}...")
            return True, "mock_twilio_sid"

        url = f"{self.BASE_URL}/Accounts/{self.account_sid}/Messages.json"
        data = {"To": to_phone, "From": self.from_number, "Body": body}

        try:
            with httpx.Client(timeout=30) as client:
                r = client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                    headers={"Accept": "application/json"},
                )
        except Exception as e:
            logger.exception("[TWILIO] Request failed")
            return False, str(e)

        if r.status_code in (200, 201):
            out = r.json()
            sid = out.get("sid")
            logger.info(f"[TWILIO] Sent to {to_phone} sid={sid}")
            return True, sid
        logger.warning(f"[TWILIO] {r.status_code} {r.text}")
        return False, r.text
