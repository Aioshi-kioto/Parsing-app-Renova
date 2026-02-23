#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый запуск: 2-3 пермита с каждого города.
Браузер видимый (headless=false), Excel в data/
"""
import asyncio
from datetime import datetime

from src.scraper import MyBuildingPermitScraper
from src.export import export_to_excel
from config import TEST_MODE_LIMIT, BROWSER_CONFIG

# Mini тест: 2 города × 2 пермита
QUICK_TEST_CITIES = ["Auburn", "Bellevue"]
QUICK_TEST_LIMIT = 2

if __name__ == "__main__":
    print("=" * 60)
    print("MyBuildingPermit Test Run")
    print(f"Cities: {len(QUICK_TEST_CITIES)}")
    print(f"Limit: {QUICK_TEST_LIMIT} permits per city")
    print(f"Browser: {'headless' if BROWSER_CONFIG['headless'] else 'visible'}")
    print("=" * 60)

    async def run():
        scraper = MyBuildingPermitScraper()
        try:
            results = await scraper.run_test_mode(
                cities=QUICK_TEST_CITIES,
                limit_per_city=QUICK_TEST_LIMIT,
                days_back=7,  # неделя: сегодня и 7 дней назад
            )
            valid = [r for r in results if not r.error]
            errors = [r for r in results if r.error]
            print(f"\n=== Results: {len(valid)} ok, {len(errors)} errors ===")
            if valid:
                data = [r.to_dict() for r in valid]
                fn = f"permits_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                path = export_to_excel(data, fn)
                print(f"Excel saved: {path}")
            owner_builders = [r for r in valid if r.is_owner_builder]
            print(f"Owner-Builder: {len(owner_builders)}")
        finally:
            await scraper.close()

    asyncio.run(run())
