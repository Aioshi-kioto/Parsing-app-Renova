# -*- coding: utf-8 -*-
"""
Утилиты для Decodo Residential Proxy → Playwright.

PROXY_URL в формате: http://USER:PASS@HOST:PORT
Документация: docs/integrations/decodo/README.md
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional
from urllib.parse import quote, unquote, urlparse, urlunparse


def proxy_url_from_env() -> Optional[str]:
    """Возвращает PROXY_URL из окружения, если задан и не пустой."""
    url = (os.environ.get("PROXY_URL") or "").strip()
    return url or None


def normalize_proxy_url_for_playwright(proxy_url: str) -> str:
    """
    Decodo (и большинство residential) — это HTTP-прокси с CONNECT для HTTPS-сайтов.
    Если в .env указали https://user:pass@gate... Playwright часто ведёт себя лучше с http://
    на той же паре host:port (иначе возможны таймауты / ERR_PROXY).
    """
    parsed = urlparse(proxy_url.strip())
    host = (parsed.hostname or "").lower()
    scheme = (parsed.scheme or "http").lower()
    if host.endswith("decodo.com") and scheme == "https":
        return urlunparse(
            (
                "http",
                parsed.netloc,
                parsed.path or "",
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
    return proxy_url.strip()


def playwright_proxy_config(proxy_url: str) -> Dict[str, Any]:
    """
    Преобразует PROXY_URL в словарь для Playwright launch() / new_context(proxy=...).

    Playwright ожидает: server, username, password (опционально).
    """
    proxy_url = normalize_proxy_url_for_playwright(proxy_url)
    parsed = urlparse(proxy_url)
    if not parsed.hostname or parsed.port is None:
        raise ValueError(f"Invalid PROXY_URL (need host and port): {proxy_url!r}")
    scheme = parsed.scheme or "http"
    server = f"{scheme}://{parsed.hostname}:{parsed.port}"
    user = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    cfg: Dict[str, Any] = {"server": server}
    if user is not None:
        cfg["username"] = user
    if password is not None:
        cfg["password"] = password
    return cfg


def build_sticky_proxy_url(
    base_user: str,
    password: str,
    host: str = "gate.decodo.com",
    port: int = 10001,
    session_id: Optional[str] = None,
) -> str:
    """
    Собирает URL для sticky session (один IP на сессию).

    Формат session в username уточняйте в доке Decodo (часто -session-<id>).
    По таблице endpoints: gate.decodo.com sticky ports 10001-49999 (см. help.decodo.com).
    """
    sid = session_id or uuid.uuid4().hex[:16]
    user = f"{base_user}-session-{sid}"
    u = quote(user, safe="")
    p = quote(password, safe="")
    return f"http://{u}:{p}@{host}:{port}"


def us_rotating_proxy_url(user: str, password: str) -> str:
    """Ротирующий US pool: us.decodo.com:10000 (см. Endpoints & Ports)."""
    return f"http://{quote(user, safe='')}:{quote(password, safe='')}@us.decodo.com:10000"
