"""
Cost calculation service.
Aggregates billing_logs usage against provider_cost_policies / provider_budgets.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from backend.database import get_connection, dict_factory
except ImportError:
    from database import get_connection, dict_factory


PROVIDERS = ("batchdata", "lob", "sendgrid", "decodo", "sms_beta")


def _q(cursor, sql, params=()):
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception:
        return []


def _q1(cursor, sql, params=()):
    try:
        cursor.execute(sql, params)
        return cursor.fetchone()
    except Exception:
        return None


def get_all_policies() -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = dict_factory
    rows = _q(conn.cursor(), "SELECT * FROM provider_cost_policies ORDER BY provider, effective_from DESC")
    conn.close()
    return rows


def get_active_policy(provider: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = dict_factory
    row = _q1(
        conn.cursor(),
        "SELECT * FROM provider_cost_policies WHERE provider=? AND is_active=true ORDER BY effective_from DESC LIMIT 1",
        (provider,),
    )
    conn.close()
    return row


def upsert_policy(provider: str, pricing_mode: str, unit_cost_usd: float, unit_name: str) -> Dict[str, Any]:
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE provider_cost_policies SET is_active=false WHERE provider=? AND is_active=true",
        (provider,),
    )
    cursor.execute(
        """INSERT INTO provider_cost_policies (provider, pricing_mode, unit_cost_usd, unit_name, is_active, effective_from)
           VALUES (?, ?, ?, ?, true, ?)
           RETURNING *""",
        (provider, pricing_mode, unit_cost_usd, unit_name, datetime.now(timezone.utc).isoformat()),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row


def get_all_budgets() -> List[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = dict_factory
    rows = _q(conn.cursor(), "SELECT * FROM provider_budgets ORDER BY provider")
    conn.close()
    return rows


def get_budget(provider: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.row_factory = dict_factory
    row = _q1(conn.cursor(), "SELECT * FROM provider_budgets WHERE provider=?", (provider,))
    conn.close()
    return row


def upsert_budget(provider: str, budget_usd: float, warning_pct: int = 80, hard_limit_enabled: bool = False) -> Dict[str, Any]:
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO provider_budgets (provider, budget_usd, warning_pct, hard_limit_enabled, updated_at)
           VALUES (?, ?, ?, ?, NOW())
           ON CONFLICT (provider) DO UPDATE
           SET budget_usd=EXCLUDED.budget_usd,
               warning_pct=EXCLUDED.warning_pct,
               hard_limit_enabled=EXCLUDED.hard_limit_enabled,
               updated_at=NOW()
           RETURNING *""",
        (provider, budget_usd, warning_pct, hard_limit_enabled),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row


def get_billing_summary() -> Dict[str, Any]:
    """
    Returns per-provider summary: actual usage from billing_logs, estimated cost from policy, budget status.
    """
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    usage_rows = _q(
        cursor,
        """SELECT service_name, COUNT(*) as events_count, SUM(cost_usd) as actual_cost
           FROM billing_logs
           WHERE date >= ?
           GROUP BY service_name""",
        (month_start,),
    )
    usage_map = {r["service_name"]: r for r in usage_rows}

    policies = _q(cursor, "SELECT * FROM provider_cost_policies WHERE is_active=true")
    policy_map = {p["provider"]: p for p in policies}

    budgets = _q(cursor, "SELECT * FROM provider_budgets")
    budget_map = {b["provider"]: b for b in budgets}

    lead_counts = _q1(cursor, """
        SELECT
            COUNT(sent_lob_at) as lob_sent,
            COUNT(sent_sendgrid_at) as sendgrid_sent,
            COUNT(skip_traced_at) as batchdata_matches
        FROM leads
    """)

    conn.close()

    result = {}
    for prov in PROVIDERS:
        u = usage_map.get(prov, {})
        p = policy_map.get(prov, {})
        b = budget_map.get(prov, {})

        events = u.get("events_count") or 0
        actual_cost = u.get("actual_cost") or 0.0
        unit_cost = p.get("unit_cost_usd") or 0.0
        estimated_cost = round(events * unit_cost, 4) if p.get("pricing_mode") == "per_event" else actual_cost

        budget_usd = b.get("budget_usd") or 0.0
        warning_pct = b.get("warning_pct") or 80
        used_pct = round(estimated_cost / budget_usd * 100, 1) if budget_usd > 0 else 0.0
        remaining = round(budget_usd - estimated_cost, 2) if budget_usd > 0 else 0.0

        if budget_usd <= 0:
            status = "no_budget"
        elif used_pct >= 100:
            status = "over_budget"
        elif used_pct >= warning_pct:
            status = "warning"
        else:
            status = "ok"

        entry: Dict[str, Any] = {
            "total_cost": round(actual_cost, 4),
            "estimated_cost": round(estimated_cost, 4),
            "success_count": events,
            "unit_cost_usd": unit_cost,
            "unit_name": p.get("unit_name", "event"),
            "pricing_mode": p.get("pricing_mode", "per_event"),
            "budget_usd": budget_usd,
            "budget_used_pct": used_pct,
            "remaining_usd": remaining,
            "status": status,
            "is_active": p.get("is_active", prov != "sms_beta"),
        }

        if prov == "lob" and lead_counts:
            entry["actual_sent"] = lead_counts.get("lob_sent", 0)
        elif prov == "sendgrid" and lead_counts:
            entry["actual_sent"] = lead_counts.get("sendgrid_sent", 0)
        elif prov == "batchdata" and lead_counts:
            entry["actual_matches"] = lead_counts.get("batchdata_matches", 0)

        result[prov] = entry

    return result


def log_billing_event(service_name: str, event_type: str, cost_usd: float, lead_id: str = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO billing_logs (service_name, event_type, cost_usd, lead_id, date) VALUES (?, ?, ?, ?, NOW()) RETURNING id",
        (service_name, event_type, cost_usd, lead_id),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row[0] if row else 0
