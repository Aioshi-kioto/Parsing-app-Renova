from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

try:
    from backend.core.parser_settings_store import (
        apply_settings_to_pending_jobs,
        get_parser_settings,
        upsert_parser_settings,
    )
except ImportError:
    from core.parser_settings_store import (
        apply_settings_to_pending_jobs,
        get_parser_settings,
        upsert_parser_settings,
    )


router = APIRouter()


class ParserSettingsPayload(BaseModel):
    config: Dict[str, Any] = {}
    channels: Dict[str, bool] = {}
    fixed_settings: Dict[str, Any] = {}


class ApplyToNextPayload(BaseModel):
    parser_type: str
    channels: Optional[Dict[str, bool]] = None
    config: Optional[Dict[str, Any]] = None


def _validate_parser_type(parser_type: str) -> str:
    parser_type = (parser_type or "").strip().lower()
    if parser_type not in ("permit", "mybuilding"):
        raise HTTPException(status_code=400, detail="Unsupported parser_type")
    return parser_type


@router.get("/{parser_type}")
async def get_settings(parser_type: str):
    parser_type = _validate_parser_type(parser_type)
    return {
        "parser_type": parser_type,
        **get_parser_settings(parser_type),
    }


@router.put("/{parser_type}")
async def update_settings(parser_type: str, payload: ParserSettingsPayload):
    parser_type = _validate_parser_type(parser_type)
    data = upsert_parser_settings(
        parser_type,
        {
            "config": payload.config,
            "channels": payload.channels,
            "fixed_settings": payload.fixed_settings,
        },
    )
    return {"ok": True, "parser_type": parser_type, **data}


@router.post("/apply-to-next")
async def apply_to_next(payload: ApplyToNextPayload):
    parser_type = _validate_parser_type(payload.parser_type)
    next_payload = {}
    if payload.config is not None:
        next_payload["config"] = payload.config
    if payload.channels is not None:
        next_payload["channels"] = payload.channels

    settings = upsert_parser_settings(parser_type, next_payload) if next_payload else get_parser_settings(parser_type)
    updated_jobs = apply_settings_to_pending_jobs(parser_type, settings)

    return {"ok": True, "parser_type": parser_type, "updated_jobs": updated_jobs}
