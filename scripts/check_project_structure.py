"""
Check project structure against expected profiles.

Usage:
  python scripts/check_project_structure.py --profile current
  python scripts/check_project_structure.py --profile production_prep
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent


PROFILES: Dict[str, List[str]] = {
    # Фактический минимум, который должен быть после Sprint 1.
    "current": [
        "backend/main.py",
        "backend/database.py",
        "backend/database_setup.py",
        "backend/db_models.py",
        "backend/config.py",
        "backend/routers/permits.py",
        "backend/routers/zillow.py",
        "backend/routers/mybuildingpermit.py",
        "backend/routers/leads.py",
        "backend/routers/tasks.py",
        "backend/routers/telegram.py",
        "backend/services/rules_engine.py",
        "backend/services/lead_pipeline.py",
        "backend/services/parsers/__init__.py",
        "backend/services/parsers/permit_parser.py",
        "backend/services/parsers/zillow_parser.py",
        "backend/services/parsers/mybuildingpermit_parser.py",
        "frontend/src/views/LeadPipeline.vue",
        "frontend/src/views/CallQueue.vue",
        "frontend/src/router/index.js",
        "docs/01-CURRENT-STATE.md",
        "docs/06-ARCHITECTURE.md",
    ],
    # Подготовка к целевой production-структуре (без Sprint 2-5 файлов).
    "production_prep": [
        "backend/services/parsers/__init__.py",
        "backend/services/parsers/permit_parser.py",
        "backend/services/parsers/zillow_parser.py",
        "backend/services/parsers/mybuildingpermit_parser.py",
        "backend/routers/leads.py",
        "backend/routers/tasks.py",
        "backend/routers/telegram.py",
        "backend/services/lead_pipeline.py",
        ".env.example",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(PROFILES.keys()), default="current")
    args = parser.parse_args()

    expected = PROFILES[args.profile]
    missing = [p for p in expected if not (ROOT / p).exists()]

    print(f"Profile: {args.profile}")
    print(f"Root: {ROOT}")
    print(f"Expected paths: {len(expected)}")
    print(f"Missing paths: {len(missing)}")
    if missing:
        print("\nMissing:")
        for p in missing:
            print(f"  - {p}")
        return 1

    print("OK: structure matches selected profile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

