"""
Download Seattle Building Permits - Owner Builder Candidates
Загружает пермиты Single Family/Duplex без указанного контрактора
"""
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime

# Directories
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API
DATASET_URL = "https://data.seattle.gov/resource/76t5-zqzr.json"


def fetch_owner_builder_candidates(
    year: int = 2025,
    min_cost: int = 5000,
    limit: int = 50000
) -> pd.DataFrame:
    """
    Fetch permits that are potential owner-builder projects:
    - Single Family / Duplex
    - Building permit type
    - No contractor specified
    - Above minimum cost threshold
    """
    
    # Build SoQL query
    conditions = [
        f"applieddate >= '{year}-01-01'",
        "permitclass = 'Single Family/Duplex'",
        "contractorcompanyname IS NULL",
    ]
    
    if min_cost:
        conditions.append(f"estprojectcost >= {min_cost}")
    
    where_clause = " AND ".join(conditions)
    
    params = {
        "$where": where_clause,
        "$limit": str(limit),
        "$order": "applieddate DESC",
    }
    
    print(f"Fetching owner-builder candidates from Seattle Open Data...")
    print(f"Filter: {where_clause}")
    
    with httpx.Client(timeout=120) as client:
        resp = client.get(DATASET_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    
    df = pd.DataFrame(data)
    print(f"Fetched: {len(df)} records")
    
    return df


def fetch_all_single_family(year: int = 2025, limit: int = 50000) -> pd.DataFrame:
    """Fetch all Single Family permits for comparison"""
    
    conditions = [
        f"applieddate >= '{year}-01-01'",
        "permitclass = 'Single Family/Duplex'",
    ]
    
    where_clause = " AND ".join(conditions)
    params = {
        "$where": where_clause,
        "$limit": str(limit),
        "$order": "applieddate DESC",
    }
    
    print(f"\nFetching ALL Single Family permits for {year}...")
    
    with httpx.Client(timeout=120) as client:
        resp = client.get(DATASET_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    
    df = pd.DataFrame(data)
    print(f"Fetched: {len(df)} records")
    
    return df


def analyze_and_save(df: pd.DataFrame, prefix: str = "permits") -> Path:
    """Analyze data and save to CSV"""
    
    if df.empty:
        print("No data to analyze")
        return None
    
    print("\n" + "="*70)
    print("DATA ANALYSIS")
    print("="*70)
    
    print(f"\nTotal records: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    
    # Date range
    if "applieddate" in df.columns:
        df["applieddate"] = pd.to_datetime(df["applieddate"])
        print(f"Date range: {df['applieddate'].min().date()} to {df['applieddate'].max().date()}")
    
    # Permit types
    if "permittypemapped" in df.columns:
        print(f"\nPermit types:")
        for typ, cnt in df["permittypemapped"].value_counts().head(10).items():
            print(f"  - {typ}: {cnt}")
    
    # Project costs
    if "estprojectcost" in df.columns:
        df["estprojectcost"] = pd.to_numeric(df["estprojectcost"], errors="coerce")
        costs = df["estprojectcost"].dropna()
        if len(costs) > 0:
            print(f"\nProject costs:")
            print(f"  - Average: ${costs.mean():,.0f}")
            print(f"  - Median: ${costs.median():,.0f}")
            print(f"  - Min: ${costs.min():,.0f}")
            print(f"  - Max: ${costs.max():,.0f}")
    
    # Contractor status
    if "contractorcompanyname" in df.columns:
        no_contractor = df["contractorcompanyname"].isna().sum()
        has_contractor = len(df) - no_contractor
        print(f"\nContractor status:")
        print(f"  - No contractor (owner-builder candidates): {no_contractor}")
        print(f"  - Has contractor: {has_contractor}")
    
    # Sample addresses
    if "originaladdress1" in df.columns:
        print(f"\nSample addresses (first 10):")
        for i, row in df.head(10).iterrows():
            addr = row.get("originaladdress1", "N/A")
            cost = row.get("estprojectcost", 0)
            desc = str(row.get("description", ""))[:50]
            print(f"  - {addr} | ${cost:,.0f} | {desc}...")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = OUTPUT_DIR / f"{prefix}_{timestamp}.csv"
    df.to_csv(filepath, index=False)
    print(f"\nSaved to: {filepath}")
    
    return filepath


def main():
    print("="*70)
    print("SEATTLE OWNER-BUILDER TRACKER")
    print("="*70)
    
    # Try 2025 first (most likely to have data)
    for year in [2025, 2024, 2023]:
        print(f"\n>>> Trying year {year}...")
        
        # Get all Single Family permits
        all_df = fetch_all_single_family(year=year, limit=10000)
        
        if len(all_df) > 0:
            print(f"\nFound {len(all_df)} Single Family permits for {year}")
            
            # Analyze contractor distribution
            if "contractorcompanyname" in all_df.columns:
                no_contractor = all_df["contractorcompanyname"].isna().sum()
                print(f"Without contractor: {no_contractor} ({no_contractor/len(all_df)*100:.1f}%)")
            
            # Filter for owner-builder candidates
            owner_builder_df = all_df[all_df["contractorcompanyname"].isna()].copy()
            
            # Filter by cost if available
            if "estprojectcost" in owner_builder_df.columns:
                owner_builder_df["estprojectcost"] = pd.to_numeric(
                    owner_builder_df["estprojectcost"], errors="coerce"
                )
                owner_builder_df = owner_builder_df[
                    (owner_builder_df["estprojectcost"] >= 5000) | 
                    (owner_builder_df["estprojectcost"].isna())
                ]
            
            print(f"Owner-builder candidates (no contractor, cost >= $5000): {len(owner_builder_df)}")
            
            # Save both
            analyze_and_save(all_df, f"all_single_family_{year}")
            
            if len(owner_builder_df) > 0:
                analyze_and_save(owner_builder_df, f"owner_builder_candidates_{year}")
            
            break
        else:
            print(f"No data for {year}")
    
    print("\n" + "="*70)
    print("DONE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Review CSV files in output/ folder")
    print("2. For Playwright verification: python main.py verify <csv_file>")


if __name__ == "__main__":
    main()
