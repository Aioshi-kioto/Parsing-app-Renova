#!/usr/bin/env python3
"""
Быстрый прогон MBP по трём городам (без UI): Playwright + опционально Decodo.

Из корня репозитория:
  pip install python-dotenv playwright
  playwright install chromium
  python scripts/run_mbp_three_cities.py

БД не обязательна: скрипт только гоняет скрапер и печатает строки. Для прокси задайте PROXY_URL в .env.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cities",
        default="Bellevue,Kirkland,Sammamish",
        help="Через запятую, имена как в UI",
    )
    parser.add_argument("--limit", type=int, default=15, help="Макс. записей на город")
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    args = parser.parse_args()
    cities = [c.strip() for c in args.cities.split(",") if c.strip()]

    async def _run():
        from services.mbp_playwright_scraper import MyBuildingPermitScraper

        proxy = (os.environ.get("PROXY_URL") or "").strip() or None
        if proxy:
            from utils.decodo_proxy import normalize_proxy_url_for_playwright

            proxy = normalize_proxy_url_for_playwright(proxy)

        scraper = MyBuildingPermitScraper(headless=args.headless, proxy_url=proxy)

        def progress(*a, **kw):
            print("[progress]", a, kw)

        results, stats = await scraper.run_with_adaptive_dates(
            cities=cities,
            limit_per_city=args.limit,
            progress_callback=progress,
            days_back=args.days_back,
        )
        print(f"OK: {len(results)} permits, stats={stats}")
        for r in results[:8]:
            print(" ", r.permit_number, r.jurisdiction, r.address, r.permit_type)
        if len(results) > 8:
            print(f"  ... +{len(results) - 8} more")
        return 0

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
