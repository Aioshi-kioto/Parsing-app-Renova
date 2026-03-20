import json
from datetime import datetime
from typing import Any, Dict

try:
    from backend.database import get_connection, dict_factory
except ImportError:
    from database import get_connection, dict_factory


DEFAULT_PERMIT_SETTINGS = {
    "config": {
        "year": datetime.utcnow().year,
        "month": None,
        "permit_class": "Single Family / Duplex",
        "min_cost": 5000,
        "verify_owner_builder": True,
        "browser_visible": True,
    },
    "channels": {
        "physical_mail": True,
        "email": True,
        "enrichment": True,
    },
    "fixed_settings": {
        "source": "Seattle SDCI",
        "check_owner_builder_always": True,
    },
}


DEFAULT_MBP_SETTINGS = {
    "config": {
        "jurisdictions": ["Bellevue", "Kirkland", "Sammamish"],
        "days_back": 7,
        "browser_visible": True,
    },
    "channels": {
        "physical_mail": True,
        "email": True,
        "enrichment": True,
    },
    "fixed_settings": {
        "source": "MyBuildingPermit",
        "parse_all_selected_cities": True,
    },
}


def _defaults(parser_type: str) -> Dict[str, Any]:
    return DEFAULT_PERMIT_SETTINGS if parser_type == "permit" else DEFAULT_MBP_SETTINGS


def ensure_parser_settings_table() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS parser_settings (
            parser_type VARCHAR PRIMARY KEY,
            config_json JSONB,
            channels_json JSONB,
            fixed_settings_json JSONB,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    conn.commit()
    conn.close()


def get_parser_settings(parser_type: str) -> Dict[str, Any]:
    ensure_parser_settings_table()
    defaults = _defaults(parser_type)
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parser_settings WHERE parser_type = ?", (parser_type,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return defaults
    return {
        "config": row.get("config_json") or defaults["config"],
        "channels": row.get("channels_json") or defaults["channels"],
        "fixed_settings": row.get("fixed_settings_json") or defaults["fixed_settings"],
    }


def upsert_parser_settings(parser_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ensure_parser_settings_table()
    merged = get_parser_settings(parser_type)
    merged["config"] = {**merged.get("config", {}), **(payload.get("config") or {})}
    merged["channels"] = {**merged.get("channels", {}), **(payload.get("channels") or {})}
    merged["fixed_settings"] = {**merged.get("fixed_settings", {}), **(payload.get("fixed_settings") or {})}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO parser_settings (parser_type, config_json, channels_json, fixed_settings_json, updated_at)
        VALUES (?, ?::jsonb, ?::jsonb, ?::jsonb, NOW())
        ON CONFLICT (parser_type) DO UPDATE SET
            config_json = EXCLUDED.config_json,
            channels_json = EXCLUDED.channels_json,
            fixed_settings_json = EXCLUDED.fixed_settings_json,
            updated_at = NOW()
        """,
        (
            parser_type,
            json.dumps(merged["config"]),
            json.dumps(merged["channels"]),
            json.dumps(merged["fixed_settings"]),
        ),
    )
    conn.commit()
    conn.close()
    return merged


def apply_settings_to_pending_jobs(parser_type: str, settings: Dict[str, Any]) -> int:
    config = settings.get("config") or {}
    conn = get_connection()
    cursor = conn.cursor()
    updated = 0

    if parser_type == "permit":
        set_parts = []
        params = []
        if config.get("year") is not None:
            set_parts.append("year = ?")
            params.append(config["year"])
        if config.get("permit_class") is not None:
            set_parts.append("permit_class_filter = ?")
            params.append(config["permit_class"])
        if config.get("min_cost") is not None:
            set_parts.append("min_cost = ?")
            params.append(config["min_cost"])
        if set_parts:
            cursor.execute(
                f"UPDATE permit_jobs SET {', '.join(set_parts)} WHERE status IN ('pending','queued','scheduled')",
                params,
            )
            updated = cursor.rowcount or 0
    elif parser_type == "mybuilding":
        set_parts = []
        params = []
        if config.get("days_back") is not None:
            set_parts.append("days_back = ?")
            params.append(config["days_back"])
        if config.get("jurisdictions") is not None:
            set_parts.append("jurisdictions = ?")
            params.append(json.dumps(config["jurisdictions"]))
        if set_parts:
            cursor.execute(
                f"UPDATE mbp_jobs SET {', '.join(set_parts)} WHERE status IN ('pending','queued','scheduled')",
                params,
            )
            updated = cursor.rowcount or 0

    conn.commit()
    conn.close()
    return updated
