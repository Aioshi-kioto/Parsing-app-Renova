"""Quick data status report"""
import pandas as pd
from pathlib import Path
import json

data_dir = Path("data")
output_dir = Path("output")

# Data folder
print("=" * 60)
print("DATA FOLDER (data/)")
print("=" * 60)

for f in sorted(data_dir.iterdir()):
    if f.suffix == ".csv":
        df = pd.read_csv(f)
        print(f"  {f.name}: {len(df)} rows")
    elif f.suffix == ".json":
        with open(f) as fp:
            j = json.load(fp)
        print(f"  {f.name}: {j}")

# Output folder
print("\n" + "=" * 60)
print("OUTPUT FOLDER (output/)")
print("=" * 60)

for f in sorted(output_dir.iterdir()):
    if f.suffix == ".csv":
        df = pd.read_csv(f)
        print(f"  {f.name}: {len(df)} rows")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

all_sf = output_dir / "all_single_family_2025_20260129_015346.csv"
candidates = output_dir / "owner_builder_candidates_2025_20260129_015346.csv"
master = output_dir / "master_owner_builders.csv"

if all_sf.exists():
    df = pd.read_csv(all_sf)
    print(f"All Single Family/Duplex (2025): {len(df)} rows - filter: permitclass only")
if candidates.exists():
    df = pd.read_csv(candidates)
    print(f"Owner-builder candidates: {len(df)} rows - all filters applied at API")
if master.exists():
    df = pd.read_csv(master)
    print(f"Master file (daily_update): {len(df)} rows")
