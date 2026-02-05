"""Check unknown records"""
import pandas as pd

df = pd.read_csv("output/jan2026_all_results.csv")
unknown = df[df["is_owner_builder"].isna()]

print(f"Unknown records: {len(unknown)}")
print()
print("Errors breakdown:")
print(unknown["scrape_error"].value_counts().head(10))
print()

# Check those without errors but still unknown
no_error_unknown = unknown[unknown["scrape_error"].isna()]
print(f"Unknown WITHOUT scrape error: {len(no_error_unknown)}")

print()
print("Sample unknown work_performer_text:")
for i, row in no_error_unknown.head(5).iterrows():
    wpt = row["work_performer_text"]
    if pd.notna(wpt):
        print(f"  {row['PermitNum']}: {wpt[:80]}...")
    else:
        print(f"  {row['PermitNum']}: NO work_performer_text found")
