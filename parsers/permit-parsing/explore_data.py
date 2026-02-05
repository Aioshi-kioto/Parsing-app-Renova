"""Explore Seattle Building Permits data structure"""
import httpx
import pandas as pd
from pathlib import Path

# Create data folder
Path("data").mkdir(exist_ok=True)
Path("output").mkdir(exist_ok=True)

# Dataset
url = "https://data.seattle.gov/resource/76t5-zqzr.json"

print("="*70)
print("EXPLORING SEATTLE BUILDING PERMITS DATA")
print("="*70)

# Fetch more data with all fields
params = {
    "$limit": "1000",
}

print("\nFetching 1000 records...")
with httpx.Client(timeout=120) as client:
    resp = client.get(url, params=params)
    data = resp.json()

df = pd.DataFrame(data)
print(f"Records: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\n" + "-"*70)
print("ALL COLUMNS WITH SAMPLE VALUES:")
print("-"*70)
for col in sorted(df.columns):
    non_null = df[col].dropna()
    sample = str(non_null.iloc[0])[:60] if len(non_null) > 0 else "ALL NULL"
    null_pct = (df[col].isna().sum() / len(df)) * 100
    print(f"{col:35} | NULL: {null_pct:5.1f}% | Sample: {sample}")

# Save full data
df.to_csv("data/full_sample.csv", index=False)
print(f"\nSaved to data/full_sample.csv")

# Check for date-like columns
print("\n" + "-"*70)
print("LOOKING FOR DATE COLUMNS:")
print("-"*70)
for col in df.columns:
    sample = df[col].dropna().head(1).tolist()
    if sample:
        val = str(sample[0])
        if "202" in val or "date" in col.lower():
            print(f"  {col}: {val}")

# Check permit classes
print("\n" + "-"*70)
print("PERMIT CLASSES:")
print("-"*70)
if "permitclass" in df.columns:
    for cls, cnt in df["permitclass"].value_counts().items():
        print(f"  {cls}: {cnt}")

# Check for self-builder indicators
print("\n" + "-"*70)
print("CONTRACTOR DATA:")
print("-"*70)
contractor_cols = [c for c in df.columns if "contractor" in c.lower()]
print(f"Contractor columns: {contractor_cols}")
for col in contractor_cols:
    non_null = df[col].dropna()
    print(f"  {col}: {len(non_null)}/{len(df)} non-null")
    if len(non_null) > 0:
        print(f"    Sample values: {non_null.head(3).tolist()}")

# Filter Single Family permits
print("\n" + "-"*70)
print("SINGLE FAMILY / DUPLEX PERMITS:")
print("-"*70)
if "permitclass" in df.columns:
    sf_df = df[df["permitclass"].str.contains("Single Family", case=False, na=False)]
    print(f"Single Family/Duplex: {len(sf_df)} records")
    
    if len(sf_df) > 0:
        sf_df.to_csv("output/single_family_permits.csv", index=False)
        print("Saved to output/single_family_permits.csv")
        
        # Show sample addresses
        if "originaladdress1" in sf_df.columns:
            print("\nSample addresses:")
            for addr in sf_df["originaladdress1"].head(10):
                print(f"  - {addr}")
