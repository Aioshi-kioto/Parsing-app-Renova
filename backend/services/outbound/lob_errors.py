"""
Lob API — парсинг и классификация ошибок.

Используется в lob_client и в тестах test/lob.
Справочник: docs/integrations/lob/ERROR_CODES.md
"""
from typing import Optional, Dict, Any, Tuple


def parse_lob_error(response_text: str, status_code: int) -> Dict[str, Any]:
    """
    Парсит тело ответа Lob при ошибке.
    Lob возвращает: {"error": {"message": "...", "code": "...", "status_code": 401}}
    """
    result = {
        "status_code": status_code,
        "code": None,
        "message": None,
        "retryable": False,
        "action": "investigate",
    }
    try:
        import json
        data = json.loads(response_text)
        err = data.get("error") or data
        result["code"] = err.get("code") or err.get("error", {}).get("code")
        result["message"] = err.get("message") or str(err)
    except Exception:
        result["message"] = response_text[:500]

    # Классификация по status_code (Lob Error Reference)
    if status_code == 401 or status_code == 403:
        result["action"] = "check_api_key"
        result["retryable"] = False
    elif status_code == 404:
        result["action"] = "retry_later"  # resource may not be created yet
        result["retryable"] = True
    elif status_code == 429:
        result["action"] = "backoff_5_sec"
        result["retryable"] = True
    elif 500 <= status_code < 600:
        result["action"] = "retry_with_backoff"
        result["retryable"] = True
    elif status_code in (400, 422):
        result["action"] = "fix_request"
        result["retryable"] = False

    return result


def format_lob_error_for_log(parsed: Dict[str, Any]) -> str:
    """Форматирует распарсенную ошибку для лога/алерта."""
    parts = ["Lob API error %s" % parsed["status_code"]]
    if parsed.get("code"):
        parts.append("code=%s" % parsed["code"])
    if parsed.get("message"):
        parts.append("message=%s" % (parsed["message"][:200] if len(str(parsed["message"])) > 200 else parsed["message"]))
    parts.append("action=%s" % parsed.get("action", "investigate"))
    return " | ".join(parts)
