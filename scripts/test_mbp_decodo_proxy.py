#!/usr/bin/env python3
"""
Проверка Decodo + Playwright перед полным парсингом MyBuildingPermit.

Делает:
1) Запрос через прокси к https://ip.decodo.com/json (проверка учётки).
2) Открытие https://permitsearch.mybuildingpermit.com/ (дымовой тест MBP).

Запуск из корня репозитория (с активированным venv с playwright):
  pip install python-dotenv playwright
  playwright install chromium
  python scripts/test_mbp_decodo_proxy.py

Переменные (.env в корне):
  PROXY_URL=http://USER:PASS@gate.decodo.com:7000
  # опционально — отчёт по трафику (ключ из dashboard Decodo, см. docs/integrations/decodo/README.md):
  DECODO_API_KEY=

Оценка расходов: после прогона смотри Decodo Dashboard → Residential → Usage statistics
или API POST https://api.decodo.com/api/v2/statistics/traffic
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Корень репо
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import httpx
except ImportError:
    httpx = None


def load_env() -> None:
    env_path = ROOT / ".env"
    if load_dotenv and env_path.is_file():
        load_dotenv(env_path)


def check_ip_via_requests(proxy_url: str) -> dict:
    if not httpx:
        print("httpx не установлен, пропуск HTTP-проверки ip.decodo.com (pip install httpx)")
        return {}
    r = httpx.get(
        "https://ip.decodo.com/json",
        proxy=proxy_url,
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


def check_ip_via_playwright(proxy_url: str, headless: bool) -> dict:
    from playwright.sync_api import sync_playwright

    from backend.utils.decodo_proxy import playwright_proxy_config

    cfg = playwright_proxy_config(proxy_url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, proxy=cfg)
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=False,
            )
            page = context.new_page()
            page.goto("https://ip.decodo.com/json", timeout=120000)
            text = page.inner_text("body")
            data = json.loads(text.strip())
            context.close()
            return data
        finally:
            browser.close()


def smoke_mbp(proxy_url: str, headless: bool, timeout_ms: int) -> dict:
    from playwright.sync_api import sync_playwright

    from backend.utils.decodo_proxy import playwright_proxy_config

    cfg = playwright_proxy_config(proxy_url)
    url = "https://permitsearch.mybuildingpermit.com/"
    t0 = time.perf_counter()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, proxy=cfg)
        try:
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()
            resp = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            status = resp.status if resp else None
            title = page.title()
            context.close()
            elapsed = time.perf_counter() - t0
            return {
                "mbp_url": url,
                "http_status": status,
                "title": title,
                "elapsed_sec": round(elapsed, 2),
            }
        finally:
            browser.close()


def fetch_traffic_stats(api_key: str, days: int = 7) -> None:
    if not httpx:
        print("httpx нужен для --stats (pip install httpx)")
        return
    from datetime import datetime, timedelta

    end = datetime.utcnow()
    start = end - timedelta(days=days)
    body = {
        "proxyType": "residential_proxies",
        "startDate": start.strftime("%Y-%m-%d 00:00:00"),
        "endDate": end.strftime("%Y-%m-%d 23:59:59"),
        "groupBy": "day",
        "limit": 500,
        "page": 1,
        "sortBy": "grouping_key",
        "sortOrder": "asc",
    }
    r = httpx.post(
        "https://api.decodo.com/api/v2/statistics/traffic",
        headers={
            "Authorization": api_key,
            "accept": "application/json",
            "content-type": "application/json",
        },
        json=body,
        timeout=60.0,
    )
    if r.status_code != 200:
        print(f"Statistics API: {r.status_code} {r.text[:500]}")
        return
    out = r.json()
    meta = out.get("metadata", {})
    totals = meta.get("totals", {})
    rx_tx = totals.get("total_rx_tx", 0)
    mb = rx_tx / (1024 * 1024) if rx_tx else 0
    print("\n--- Decodo traffic (API, last ~{} days) ---".format(days))
    print(f"  total_rx_tx bytes: {rx_tx}  (~{mb:.2f} MB)")
    print(f"  requests: {totals.get('requests')}")
    for row in out.get("data", [])[:14]:
        print(f"  {row}")


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description="Decodo + Playwright + MBP smoke test")
    parser.add_argument("--headless", action="store_true", help="Headless Chromium")
    parser.add_argument("--skip-mbp", action="store_true", help="Только ip.decodo.com")
    parser.add_argument("--timeout-mbp", type=int, default=120000, help="Timeout ms для MBP")
    parser.add_argument("--stats", action="store_true", help="Вызвать Statistics API (нужен DECODO_API_KEY)")
    parser.add_argument("--stats-days", type=int, default=7)
    args = parser.parse_args()

    proxy_url = os.environ.get("PROXY_URL", "").strip()
    if not proxy_url:
        print("Задайте PROXY_URL в .env (см. docs/integrations/decodo/README.md)")
        return 1

    from backend.utils.decodo_proxy import normalize_proxy_url_for_playwright

    proxy_url = normalize_proxy_url_for_playwright(proxy_url)
    print("PROXY_URL host:", proxy_url.split("@")[-1] if "@" in proxy_url else proxy_url[:40])

    # 1) httpx через прокси (быстрая проверка)
    if httpx:
        try:
            ip_data = check_ip_via_requests(proxy_url)
            print("\n[httpx] ip.decodo.com/json:", json.dumps(ip_data, indent=2)[:800])
        except Exception as e:
            print("\n[httpx] Ошибка:", e)

    # 2) Playwright + тот же прокси
    try:
        ip_pw = check_ip_via_playwright(proxy_url, headless=args.headless)
        print("\n[Playwright] ip.decodo.com/json:", json.dumps(ip_pw, indent=2)[:800])
    except Exception as e:
        print("\n[Playwright] ip.decodo.com ошибка:", e)
        return 1

    if not args.skip_mbp:
        try:
            mbp = smoke_mbp(proxy_url, headless=args.headless, timeout_ms=args.timeout_mbp)
            print("\n[Playwright] MyBuildingPermit smoke:", json.dumps(mbp, indent=2))
        except Exception as e:
            print("\n[Playwright] MBP ошибка:", e)
            return 1

    api_key = (os.environ.get("DECODO_API_KEY") or "").strip()
    if args.stats and api_key:
        fetch_traffic_stats(api_key, days=args.stats_days)
    elif args.stats:
        print("\n--stats: задайте DECODO_API_KEY в .env")

    print(
        "\nДальше: открой Decodo Dashboard → Residential → Usage statistics — там Traffic (MB/GB),"
        " Requests, Spend (USD) и экспорт CSV/JSON."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
