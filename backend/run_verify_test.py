#!/usr/bin/env python3
"""
Тест верификации Owner-Builder на 10 пермитах.
Запуск из папки backend: python run_verify_test.py
"""
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from services.permit_parser import (
    fetch_permits_from_api,
    verify_permits_batch_async,
    portal_link_for_permit,
)


async def main():
    limit = 10
    print(f"Fetching {limit} permits from API (year=2026, month=1)...")
    try:
        raw = fetch_permits_from_api(year=2026, month=1, limit=limit, min_cost=5000)
    except Exception as e:
        print(f"API error: {e}")
        return
    if not raw:
        print("No permits returned. Try another year/month.")
        return
    permit_nums = [p.get("permitnum") for p in raw if p.get("permitnum")]
    print(f"Verifying {len(permit_nums)} permits (headless=True, batch=4)...")
    results = await verify_permits_batch_async(permit_nums, headless=True, job_id=None)
    print()
    print("Results:")
    print("-" * 80)
    for r in results:
        pn = r.get("permit_num", "")
        is_owner = r.get("is_owner_builder")
        text = r.get("work_performer_text") or ""
        err = r.get("error")
        link = portal_link_for_permit(pn)
        status = "Owner" if is_owner else "Contractor" if is_owner is False else "Unknown"
        if err:
            status = f"Error: {err[:50]}"
        print(f"  {pn} | {status} | {text[:40]} | {link}")
    print("-" * 80)
    owners = sum(1 for r in results if r.get("is_owner_builder") is True)
    contractors = sum(1 for r in results if r.get("is_owner_builder") is False)
    errors = sum(1 for r in results if r.get("error"))
    print(f"Summary: Owner/Lessee={owners}, Licensed Contractor={contractors}, errors={errors}")


if __name__ == "__main__":
    asyncio.run(main())
