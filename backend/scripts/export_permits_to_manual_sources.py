"""
Экспорт пермитов в test/manual_sources/permits/ для ручной оценки.

Собирает два CSV:
- sdci_permits.csv — из Seattle Open Data API (без запуска UI/БД).
- mbp_permits.csv — из таблицы mbp_permits в БД (нужно сначала запустить парсер MBP через UI).

Опция --from-sqlite: взять 10–20 строк из старой SQLite-базы (до миграции на PostgreSQL).

Запуск из корня проекта:
  python -m backend.scripts.export_permits_to_manual_sources [--sdci-only] [--mbp-only] [--year 2026] [--month 1]
  python -m backend.scripts.export_permits_to_manual_sources --from-sqlite backend/data/renova.db --limit 15
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Корень репозитория (parent of backend)
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

OUT_DIR = PROJECT_ROOT / "test" / "manual_sources" / "permits"
CSV_COLUMNS = [
    "address",
    "permit_type",
    "applied_date",
    "issued_date",
    "applicant_name",
    "contractor_name",
    "description",
]


def row_sdci(raw: dict, extracted: dict) -> dict:
    """Одна строка CSV из SDCI (API + extract_permit_data)."""
    return {
        "address": extracted.get("address") or "",
        "permit_type": (extracted.get("permit_type_mapped") or extracted.get("permit_type_desc")) or "",
        "applied_date": extracted.get("applied_date") or "",
        "issued_date": extracted.get("issued_date") or "",
        "applicant_name": raw.get("applicant") or "",
        "contractor_name": extracted.get("contractor_name") or "",
        "description": extracted.get("description") or "",
    }


def row_mbp(rec: dict) -> dict:
    """Одна строка CSV из записи mbp_permits."""
    return {
        "address": rec.get("address") or "",
        "permit_type": rec.get("permit_type") or "",
        "applied_date": _date_str(rec.get("applied_date")),
        "issued_date": _date_str(rec.get("issued_date")),
        "applicant_name": rec.get("applicant_name") or "",
        "contractor_name": rec.get("contractor_name") or "",
        "description": rec.get("description") or "",
    }


def _date_str(val) -> str:
    """Дата в строку YYYY-MM-DD для CSV."""
    if val is None:
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if s and len(s) >= 10:
        return s[:10]
    return s


def export_from_sqlite(sqlite_path: Path, limit: int = 15) -> tuple[Path, Path | None]:
    """
    Экспорт 10–20 строк из старой SQLite-базы (таблицы permits и mbp_permits)
    в sdci_permits.csv и mbp_permits.csv.
    """
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # SDCI: таблица permits
    cur.execute(
        """
        SELECT address, permit_type_mapped, permit_type_desc, applied_date, issued_date,
               contractor_name, description, raw_data
        FROM permits
        WHERE address IS NOT NULL AND address != ''
        ORDER BY applied_date DESC
        LIMIT ?
        """,
        (limit,),
    )
    permits_rows = [dict(r) for r in cur.fetchall()]
    sdci_path = OUT_DIR / "sdci_permits.csv"
    with open(sdci_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in permits_rows:
            applicant = ""
            if r.get("raw_data"):
                try:
                    raw = json.loads(r["raw_data"]) if isinstance(r["raw_data"], str) else r["raw_data"]
                    applicant = raw.get("applicant") or ""
                except Exception:
                    pass
            w.writerow({
                "address": r.get("address") or "",
                "permit_type": (r.get("permit_type_mapped") or r.get("permit_type_desc")) or "",
                "applied_date": _date_str(r.get("applied_date")),
                "issued_date": _date_str(r.get("issued_date")),
                "applicant_name": applicant,
                "contractor_name": r.get("contractor_name") or "",
                "description": r.get("description") or "",
            })
    print(f"[SQLite] SDCI: written {len(permits_rows)} rows -> {sdci_path}")

    # MBP: таблица mbp_permits (может отсутствовать в старых БД)
    mbp_path = None
    try:
        cur.execute(
            """
            SELECT address, permit_type, applied_date, issued_date,
                   applicant_name, contractor_name, description
            FROM mbp_permits
            WHERE address IS NOT NULL AND address != ''
            ORDER BY applied_date DESC
            LIMIT ?
            """,
            (limit,),
        )
        mbp_rows = [dict(r) for r in cur.fetchall()]
        mbp_path = OUT_DIR / "mbp_permits.csv"
        with open(mbp_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            w.writeheader()
            for r in mbp_rows:
                w.writerow(row_mbp(r))
        print(f"[SQLite] MBP: written {len(mbp_rows)} rows -> {mbp_path}")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            print("[SQLite] Table mbp_permits not found, skipping MBP CSV.")
        else:
            raise

    conn.close()
    return sdci_path, mbp_path


def export_sdci(year: int, month: int | None, limit: int = 10000) -> Path:
    """Скачать пермиты из Seattle Open Data API и записать sdci_permits.csv."""
    from services.permit_parser import fetch_permits_from_api, extract_permit_data

    raw_list = fetch_permits_from_api(
        year=year,
        month=month,
        permit_class=None,
        min_cost=0,
        limit=limit,
        contractor_is_null=False,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "sdci_permits.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for raw in raw_list:
            extracted = extract_permit_data(raw)
            w.writerow(row_sdci(raw, extracted))
    print(f"[SDCI] Written {len(raw_list)} rows -> {out_path}")
    return out_path


def export_mbp() -> Path | None:
    """Экспорт таблицы mbp_permits в mbp_permits.csv."""
    from database import get_connection, dict_factory

    conn = get_connection()
    conn.row_factory = dict_factory
    cur = conn.cursor()
    cur.execute(
        """
        SELECT address, permit_type, applied_date, issued_date,
               applicant_name, contractor_name, description
        FROM mbp_permits
        ORDER BY applied_date DESC NULLS LAST
        """
    )
    rows = cur.fetchall()
    conn.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "mbp_permits.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for rec in rows:
            w.writerow(row_mbp(rec))
    print(f"[MBP] Written {len(rows)} rows -> {out_path}")
    if not rows:
        print("[MBP] Table mbp_permits is empty. Run MBP parser via UI first, then run this script again.")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Export permits to test/manual_sources/permits/")
    parser.add_argument("--from-sqlite", type=str, metavar="PATH", help="Old SQLite DB path (e.g. backend/data/renova.db); export 10–20 rows from permits + mbp_permits")
    parser.add_argument("--sdci-only", action="store_true", help="Only export SDCI from API")
    parser.add_argument("--mbp-only", action="store_true", help="Only export MBP from DB")
    parser.add_argument("--year", type=int, default=None, help="Year for SDCI (default: current)")
    parser.add_argument("--month", type=int, default=None, help="Month for SDCI (default: all year)")
    parser.add_argument("--limit", type=int, default=10000, help="Max rows for SDCI API (default 10000); with --from-sqlite default 15")
    args = parser.parse_args()

    if args.from_sqlite:
        path = Path(args.from_sqlite)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        limit_sqlite = 15 if args.limit == 10000 else min(args.limit, 100)
        export_from_sqlite(path, limit=limit_sqlite)
        return

    now = datetime.now()
    year = args.year if args.year is not None else now.year
    month = args.month

    do_sdci = not args.mbp_only
    do_mbp = not args.sdci_only

    if do_sdci:
        export_sdci(year=year, month=month, limit=args.limit)
    if do_mbp:
        export_mbp()


if __name__ == "__main__":
    main()
