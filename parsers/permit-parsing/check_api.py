"""Quick check of Seattle API data availability"""
import httpx
import pandas as pd

url = "https://data.seattle.gov/resource/76t5-zqzr.json"

# Check latest data without strict filters
params = {
    "$limit": "100"
}

print("Checking Seattle Open Data API...")
with httpx.Client(timeout=60) as client:
    resp = client.get(url, params=params)
    data = resp.json()

df = pd.DataFrame(data)
print(f"\nRecords fetched: {len(df)}")

if len(df) > 0:
    print(f"\nAll columns ({len(df.columns)}):")
    for col in sorted(df.columns):
        sample = df[col].dropna().head(1).tolist()
        sample_str = str(sample[0])[:50] if sample else "N/A"
        print(f"  - {col}: {sample_str}")
    
    # Save sample to CSV for analysis
    df.to_csv("data/sample_permits.csv", index=False)
    print("\nSample saved to data/sample_permits.csv")
