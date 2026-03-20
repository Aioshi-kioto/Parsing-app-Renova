#!/usr/bin/env python3
"""
Экспорт пермитов из БД в test/manual_sources/permits/ для ручной оценки.

Запуск после того, как парсеры уже отработали (через UI или API):
  1. Запустить парсинг: UI → Permits и/или MyBuildingPermit.
  2. Дождаться завершения job.
  3. Выполнить: python scripts/export_permits_to_manual_sources.py

Из backend читаются таблицы permits (SDCI) и mbp_permits (MyBuildingPermit)
и записываются sdci_permits.csv и mbp_permits.csv в test/manual_sources/permits/.
"""
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
OUT_DIR = REPO_ROOT / "test" / "manual_sources" / "permits"

sys.path.insert(0, str(REPO_ROOT))

def main():
    from backend.database import get_connection, dict_factory

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    sdci_columns = [
        "address", "city", "state", "zipcode", "permit_type_mapped", "permit_type_desc",
        "applied_date", "issued_date", "description", "contractor_name", "status_current",
    ]
    cursor.execute("""
        SELECT address, city, state, zipcode, permit_type_mapped, permit_type_desc,
               applied_date, issued_date, description, contractor_name, status_current
        FROM permits
        ORDER BY applied_date DESC
    """)
    sdci_rows = cursor.fetchall()
    sdci_path = OUT_DIR / "sdci_permits.csv"
    with open(sdci_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sdci_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sdci_rows)
    print(f"SDCI: записано {len(sdci_rows)} записей в {sdci_path}")

    mbp_columns = [
        "address", "jurisdiction", "permit_type", "permit_status", "applied_date", "issued_date",
        "description", "applicant_name", "contractor_name", "parcel", "permit_url",
    ]
    cursor.execute("""
        SELECT address, jurisdiction, permit_type, permit_status, applied_date, issued_date,
               description, applicant_name, contractor_name, parcel, permit_url
        FROM mbp_permits
        ORDER BY created_at DESC
    """)
    mbp_rows = cursor.fetchall()
    mbp_path = OUT_DIR / "mbp_permits.csv"
    with open(mbp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=mbp_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(mbp_rows)
    print(f"MBP:  записано {len(mbp_rows)} записей в {mbp_path}")

    conn.close()
    print("Готово. Файлы в test/manual_sources/permits/.")


if __name__ == "__main__":
    main()
