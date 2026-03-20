"""
Outbound templates router.
Управление шаблонами и тестовые отправки через SendGrid/Lob.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.services.outbound.templates import (
        DEFAULT_TEMPLATES,
        get_all_templates,
        get_template_payload,
        get_template,
        render,
        upsert_template,
    )
    from backend.services.outbound.sendgrid_client import SendGridClient
    from backend.services.outbound.lob_client import get_lob_client
except Exception:
    from services.outbound.templates import (
        DEFAULT_TEMPLATES,
        get_all_templates,
        get_template_payload,
        get_template,
        render,
        upsert_template,
    )
    from services.outbound.sendgrid_client import SendGridClient
    from services.outbound.lob_client import get_lob_client


router = APIRouter()


class TemplateUpdate(BaseModel):
    email_subject: str = Field(default="", max_length=1000)
    email_body: str = Field(default="", max_length=100000)
    sms_body: str = Field(default="", max_length=5000)
    lob_template_id: str | None = Field(default=None, max_length=2000)
    lob_body_html: str | None = Field(default=None, max_length=100000)


class EmailTestRequest(BaseModel):
    case_type: str | None = "GENERAL"
    to_email: str
    owner_name: str = ""
    street_name: str = ""
    address: str = ""
    subject_override: str | None = None
    body_override: str | None = None


class LobTestRequest(BaseModel):
    case_type: str | None = "GENERAL"
    recipient_name: str = Field(default="Homeowner")
    address_line1: str
    address_city: str
    address_state: str = "WA"
    address_zip: str
    owner_name: str = ""
    street_name: str = ""
    address: str = ""
    lob_template_override: str | None = None


@router.get("/templates")
async def list_templates():
    return {"templates": get_all_templates()}


@router.get("/templates/{case_code}")
async def get_template_by_case(case_code: str):
    return get_template_payload(case_code)


@router.put("/templates/{case_code}")
async def update_template(case_code: str, body: TemplateUpdate):
    normalized = case_code if case_code in DEFAULT_TEMPLATES else "GENERAL"
    payload = upsert_template(
        normalized,
        {
            "email_subject": body.email_subject,
            "email_body": body.email_body,
            "sms_body": body.sms_body,
            "lob_template_id": body.lob_template_id,
            "lob_body_html": body.lob_body_html,
        },
    )
    return {"ok": True, "template": payload}


@router.post("/test-email")
async def test_email(body: EmailTestRequest):
    try:
        subj, email_text, _sms = render(
            get_template(body.case_type),
            owner_name=body.owner_name,
            street_name=body.street_name,
            address=body.address,
        )
        subject = body.subject_override if body.subject_override is not None else subj
        content = body.body_override if body.body_override is not None else email_text
        client = SendGridClient()
        ok, info = client.send_email(
            to_email=str(body.to_email),
            subject=subject,
            body_plain=content,
            disable_click_tracking=True,
        )
        if not ok:
            raise HTTPException(status_code=400, detail=f"SendGrid error: {info}")
        return {"ok": True, "message_id": info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email test failed: {e}")


@router.post("/test-lob")
async def test_lob(body: LobTestRequest):
    try:
        tpl = get_template_payload(body.case_type)
        file_payload = body.lob_template_override or tpl.get("lob_template_id") or tpl.get("lob_body_html")
        if not file_payload:
            raise HTTPException(
                status_code=400,
                detail="Lob template is empty. Set lob_template_id or lob_body_html first.",
            )

        to_address = {
            "name": body.recipient_name or "Homeowner",
            "address_line1": body.address_line1,
            "address_city": body.address_city,
            "address_state": body.address_state,
            "address_zip": body.address_zip,
            "address_country": "US",
        }
        merge_variables = {
            "owner_name": body.owner_name or body.recipient_name or "Homeowner",
            "street_name": body.street_name or body.address_line1,
            "address": body.address or body.address_line1,
        }
        lob_id = await get_lob_client().send_letter(to_address, file_payload, merge_variables)
        return {"ok": True, "lob_id": lob_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lob test failed: {e}")
