#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Обработка CSV из Export to Excel.
Скачайте результаты поиска (Export to Excel), сохраните как CSV.
Для каждого Permit # проверяется People: если Contractor License пуст — owner-builder.
"""
import asyncio
from datetime import datetime

from src.scraper import MyBuildingPermitScraper
from src.export import export_to_excel
from config import BROWSER_CONFIG, DATA_DIR

# Пример: CSV в data/
CSV_PATH = DATA_DIR / "SearchResults_test.csv"
JURISDICTION = "Auburn"
LIMIT = 3  # Тест: 3 пермита

if __name__ == "__main__":
    print("=" * 60)
    print("MyBuildingPermit CSV Mode")
    print(f"CSV: {CSV_PATH}")
    print(f"Jurisdiction: {JURISDICTION}")
    print(f"Owner-builder only: True")
    print("=" * 60)

    async def run():
        scraper = MyBuildingPermitScraper()
        try:
            results = await scraper.process_from_csv(
                csv_path=str(CSV_PATH),
                jurisdiction=JURISDICTION,
                owner_builder_only=True,
                limit=LIMIT,
            )
            valid = [r for r in results if not r.error]
            owner_builders = [r for r in valid if r.is_owner_builder]
            print(f"\n=== Results: {len(valid)} processed, {len(owner_builders)} owner-builder ===")
            if valid:
                data = [r.to_dict() for r in valid]
                fn = f"permits_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                path = export_to_excel(data, fn)
                print(f"Excel saved: {path}")
            for r in owner_builders[:10]:
                print(f"  - {r.permit_number} | {r.address} | {r.applicant_name}")
        finally:
            await scraper.close()

    asyncio.run(run())
