#!/usr/bin/env python3
"""
Ручной тест Seattle Permits API.
Запуск: python scripts/test_permits_api.py [year] [--month N] [--last-month]

Примеры:
  python scripts/test_permits_api.py              # 2025, весь год
  python scripts/test_permits_api.py 2025         # 2025, весь год  
  python scripts/test_permits_api.py 2025 --month 1   # Январь 2025
  python scripts/test_permits_api.py --last-month     # Предыдущий месяц
"""
import httpx
import sys
import argparse
from datetime import date
from pathlib import Path

DATASET_URL = "https://data.seattle.gov/resource/76t5-zqzr.json"

# Варианты permitclass из API (проверено)
PERMIT_CLASS_VARIANTS = [
    "Single Family / Duplex",   # с пробелами
    "Single Family/Duplex",     # без пробелов
]

def get_date_range(year: int, month: int = None, last_month: bool = False) -> tuple:
    """(date_from, date_to)"""
    if last_month:
        today = date.today()
        if today.month == 1:
            start = date(today.year - 1, 12, 1)
            end = date(today.year, 1, 1)
        else:
            start = date(today.year, today.month - 1, 1)
            end = date(today.year, today.month, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    
    if month:
        date_from = f"{year}-{month:02d}-01"
        date_to = f"{year}-{month+1:02d}-01" if month < 12 else f"{year+1}-01-01"
        return date_from, date_to
    
    return f"{year}-01-01", f"{year+1}-01-01"


def fetch_permits(
    year: int = 2025,
    month: int = None,
    last_month: bool = False,
    permit_class: str = "Single Family / Duplex",
    permit_type: str = "Building",
    contractor_null: bool = True,
    min_cost: int = 5000,
    limit: int = 10000,
) -> list:
    """Запрос к Seattle API"""
    date_from, date_to = get_date_range(year, month, last_month)
    
    conditions = [
        f"applieddate >= '{date_from}'",
        f"applieddate < '{date_to}'",
    ]
    
    if permit_class:
        conditions.append(f"permitclass = '{permit_class}'")
    if permit_type:
        conditions.append(f"permittypemapped = '{permit_type}'")
    if contractor_null:
        conditions.append("contractorcompanyname IS NULL")
    if min_cost:
        conditions.append(f"estprojectcost >= {min_cost}")
    
    where = " AND ".join(conditions)
    params = {
        "$where": where,
        "$limit": str(limit),
        "$order": "applieddate DESC",
    }
    
    print(f"\nQuery: {where}\n")
    
    with httpx.Client(timeout=60) as client:
        resp = client.get(DATASET_URL, params=params)
        resp.raise_for_status()
        return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Test Seattle Permits API")
    parser.add_argument("year", nargs="?", type=int, default=2025, help="Year (default: 2025)")
    parser.add_argument("--month", "-m", type=int, choices=range(1, 13), help="Month 1-12")
    parser.add_argument("--last-month", "-l", action="store_true", help="Previous calendar month")
    parser.add_argument("--no-contractor-filter", action="store_true", help="Include permits WITH contractor (all)")
    parser.add_argument("--min-cost", type=int, default=5000, help="Min project cost (default: 5000)")
    parser.add_argument("--permit-class", default="Single Family / Duplex", 
                        help="Permit class (try 'Single Family/Duplex' if 0 results)")
    parser.add_argument("--limit", type=int, default=10000)
    args = parser.parse_args()
    
    print("=" * 60)
    print("SEATTLE PERMITS API - Manual Test")
    print("=" * 60)
    
    # Пробуем разные варианты permitclass если 0 результатов
    for permit_class in [args.permit_class, "Single Family/Duplex", "Single Family / Duplex"]:
        try:
            data = fetch_permits(
                year=args.year,
                month=args.month,
                last_month=args.last_month,
                permit_class=permit_class,
                contractor_null=not args.no_contractor_filter,
                min_cost=args.min_cost,
                limit=args.limit,
            )
            
            print(f"Results: {len(data)} permits")
            
            if len(data) > 0:
                print(f"\nPermit class used: '{permit_class}'")
                print(f"\nSample (first 3):")
                for i, p in enumerate(data[:3], 1):
                    addr = p.get("originaladdress1", "N/A")
                    cost = p.get("estprojectcost", "N/A")
                    applied = p.get("applieddate", "")[:10]
                    print(f"  {i}. {addr} | ${cost} | {applied}")
                
                # Сохраняем в CSV
                out_dir = Path(__file__).parent.parent / "output"
                out_dir.mkdir(exist_ok=True)
                import json
                out_file = out_dir / f"permits_test_{args.year}_{args.month or 'all'}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\nSaved to: {out_file}")
                break
            else:
                print(f"  (trying next permit_class variant...)")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nNo data with any permit_class. Try:")
        print("  --no-contractor-filter  (include all permits)")
        print("  --permit-class ''       (no class filter)")
        print("  --min-cost 0            (no cost filter)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
