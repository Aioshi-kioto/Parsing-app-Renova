from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

try:
    from backend.services.cost_service import (
        get_all_policies, get_active_policy, upsert_policy,
        get_all_budgets, get_budget, upsert_budget,
        get_billing_summary, log_billing_event, PROVIDERS,
    )
except ImportError:
    from services.cost_service import (
        get_all_policies, get_active_policy, upsert_policy,
        get_all_budgets, get_budget, upsert_budget,
        get_billing_summary, log_billing_event, PROVIDERS,
    )

router = APIRouter()


class PolicyUpdate(BaseModel):
    pricing_mode: str = Field(..., pattern="^(per_event|per_gb|flat)$")
    unit_cost_usd: float = Field(..., ge=0)
    unit_name: str = "event"


class BudgetUpdate(BaseModel):
    budget_usd: float = Field(..., ge=0)
    warning_pct: int = Field(80, ge=0, le=100)
    hard_limit_enabled: bool = False


class BillingEventCreate(BaseModel):
    service_name: str
    event_type: str
    cost_usd: float = 0.0
    lead_id: Optional[str] = None


def _validate_provider(provider: str) -> str:
    p = provider.strip().lower()
    if p not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Провайдер '{provider}' не существует. Допустимые: {', '.join(sorted(PROVIDERS))}")
    return p


@router.get("/policies")
async def list_policies():
    return {"policies": get_all_policies()}


@router.get("/policies/{provider}")
async def get_policy(provider: str):
    p = _validate_provider(provider)
    row = get_active_policy(p)
    if not row:
        raise HTTPException(status_code=404, detail="Активная политика не найдена")
    return row


@router.put("/policies/{provider}")
async def update_policy(provider: str, body: PolicyUpdate):
    p = _validate_provider(provider)
    row = upsert_policy(p, body.pricing_mode, body.unit_cost_usd, body.unit_name)
    return {"ok": True, "policy": row}


@router.get("/budgets")
async def list_budgets():
    return {"budgets": get_all_budgets()}


@router.get("/budgets/{provider}")
async def get_budget_route(provider: str):
    p = _validate_provider(provider)
    row = get_budget(p)
    if not row:
        raise HTTPException(status_code=404, detail="Бюджет не найден")
    return row


@router.put("/budgets/{provider}")
async def update_budget(provider: str, body: BudgetUpdate):
    p = _validate_provider(provider)
    row = upsert_budget(p, body.budget_usd, body.warning_pct, body.hard_limit_enabled)
    return {"ok": True, "budget": row}


@router.get("/summary")
async def billing_summary():
    return get_billing_summary()


@router.post("/log")
async def create_billing_event(body: BillingEventCreate):
    _validate_provider(body.service_name)
    event_id = log_billing_event(body.service_name, body.event_type, body.cost_usd, body.lead_id)
    return {"ok": True, "id": event_id}
