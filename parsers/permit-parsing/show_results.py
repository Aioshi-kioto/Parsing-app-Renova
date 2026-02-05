"""Show final results summary"""
import pandas as pd
from pathlib import Path

all_df = pd.read_csv("output/jan2026_all_results.csv")
owners = pd.read_csv("output/jan2026_owners_only.csv")

print("=" * 60)
print("FINAL RESULTS: January 2026 Scrape")
print("=" * 60)
print(f"Total scraped: {len(all_df)}")
print(f"OWNERS: {len(owners)} ({len(owners)/len(all_df)*100:.1f}%)")

contractors = all_df[all_df["is_owner_builder"] == False]
print(f"Contractors: {len(contractors)} ({len(contractors)/len(all_df)*100:.1f}%)")

unknown = all_df[all_df["is_owner_builder"].isna()]
print(f"Unknown/Errors: {len(unknown)} ({len(unknown)/len(all_df)*100:.1f}%)")

# Errors breakdown
if "scrape_error" in all_df.columns:
    errors = all_df[all_df["scrape_error"].notna()]
    print(f"Scrape errors: {len(errors)}")

print()
print("Owner-Builder Statistics:")
owners["EstProjectCost"] = pd.to_numeric(owners["EstProjectCost"], errors="coerce")
print(f"  Count: {len(owners)}")
print(f"  Avg cost: ${owners['EstProjectCost'].mean():,.0f}")
print(f"  Median cost: ${owners['EstProjectCost'].median():,.0f}")
print(f"  Min cost: ${owners['EstProjectCost'].min():,.0f}")
print(f"  Max cost: ${owners['EstProjectCost'].max():,.0f}")
print(f"  TOTAL VALUE: ${owners['EstProjectCost'].sum():,.0f}")

print()
print("=" * 60)
print("SAMPLE OWNER-BUILDERS (first 15)")
print("=" * 60)
for i, row in owners.head(15).iterrows():
    print(f"{row['PermitNum']:<14} | ${row['EstProjectCost']:>12,.0f} | {row['OriginalAddress1']}")

# Export clean Excel for manual review
print()
print("=" * 60)
print("Exporting clean Excel for review...")
print("=" * 60)

# Keep only relevant columns for review
cols_for_review = [
    "PermitNum", "OriginalAddress1", "OriginalCity", "OriginalState", "OriginalZip",
    "EstProjectCost", "AppliedDate", "Description", "PermitTypeDesc",
    "HousingCategory", "Link", "is_owner_builder", "work_performer_text"
]

# Filter existing columns
cols_exist = [c for c in cols_for_review if c in owners.columns]
review_df = owners[cols_exist].copy()

# Save to Excel
excel_file = Path("output/FINAL_owner_builders_jan2026.xlsx")
review_df.to_excel(excel_file, index=False, sheet_name="Owner-Builders")
print(f"Saved: {excel_file} ({len(review_df)} records)")

# Also save clean CSV
csv_file = Path("output/FINAL_owner_builders_jan2026.csv")
review_df.to_csv(csv_file, index=False)
print(f"Saved: {csv_file}")

print()
print("DONE! Check output/FINAL_owner_builders_jan2026.xlsx")
