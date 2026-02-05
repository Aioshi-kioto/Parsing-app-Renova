"""
Full scrape of January 2026 permits - find all Owner-Builders.
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import time

print("=" * 60)
print("FULL SCRAPE: January 2026 Owner-Builder Detection")
print("=" * 60)

# Load filtered data
df = pd.read_csv("output/jan_2026_candidates.csv")
print(f"Total permits to check: {len(df)}")

# Extract URLs
def extract_url(link_str):
    if pd.isna(link_str):
        return None
    try:
        if isinstance(link_str, str):
            link_dict = eval(link_str)
            return link_dict.get("url")
    except:
        return None
    return None

df["url"] = df["Link"].apply(extract_url)

# Setup Playwright
from playwright.sync_api import sync_playwright

results = []
start_time = time.time()

with sync_playwright() as p:
    print("\nLaunching browser...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="en-US",
    )
    
    total = len(df)
    owners_found = 0
    contractors_found = 0
    errors = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        permitnum = row["PermitNum"]
        url = row["url"]
        address = row["OriginalAddress1"]
        
        result = {
            "PermitNum": permitnum,
            "PermitClass": row.get("PermitClass"),
            "PermitTypeMapped": row.get("PermitTypeMapped"),
            "PermitTypeDesc": row.get("PermitTypeDesc"),
            "Description": row.get("Description"),
            "EstProjectCost": row.get("EstProjectCost"),
            "AppliedDate": row.get("AppliedDate"),
            "OriginalAddress1": address,
            "OriginalCity": row.get("OriginalCity"),
            "OriginalState": row.get("OriginalState"),
            "OriginalZip": row.get("OriginalZip"),
            "HousingCategory": row.get("HousingCategory"),
            "Link": url,
            "is_owner_builder": None,
            "work_performer_text": None,
            "scrape_error": None,
        }
        
        if not url:
            result["scrape_error"] = "No URL"
            errors += 1
            results.append(result)
            continue
        
        try:
            page = context.new_page()
            response = page.goto(url, timeout=30000, wait_until="networkidle")
            
            if response and response.status == 200:
                page.wait_for_timeout(1500)  # Wait for dynamic content
                page_text = page.inner_text("body")
                
                # Find "Who will be performing all the work?"
                if "who will be performing" in page_text.lower():
                    idx_start = page_text.lower().find("who will be performing")
                    snippet = page_text[idx_start:idx_start+150]
                    result["work_performer_text"] = snippet.strip()
                    
                    # Determine owner/contractor
                    snippet_lower = snippet.lower()
                    if "owner" in snippet_lower and "licensed contractor" not in snippet_lower:
                        result["is_owner_builder"] = True
                        owners_found += 1
                    elif "licensed contractor" in snippet_lower:
                        result["is_owner_builder"] = False
                        contractors_found += 1
                    else:
                        result["is_owner_builder"] = None
            else:
                result["scrape_error"] = f"HTTP {response.status if response else 'None'}"
                errors += 1
            
            page.close()
            
        except Exception as e:
            result["scrape_error"] = str(e)[:100]
            errors += 1
        
        results.append(result)
        
        # Progress every 20 records
        if (i + 1) % 20 == 0 or (i + 1) == total:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate if rate > 0 else 0
            print(f"Progress: {i+1}/{total} ({(i+1)/total*100:.1f}%) | Owners: {owners_found} | Contractors: {contractors_found} | Errors: {errors} | ETA: {eta:.0f}s")
    
    browser.close()

# Create results DataFrame
results_df = pd.DataFrame(results)

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
total_scraped = len(results_df)
owners = results_df[results_df["is_owner_builder"] == True]
contractors = results_df[results_df["is_owner_builder"] == False]
unknown = results_df[results_df["is_owner_builder"].isna()]

print(f"Total scraped: {total_scraped}")
print(f"OWNERS (target): {len(owners)} ({len(owners)/total_scraped*100:.1f}%)")
print(f"Contractors: {len(contractors)} ({len(contractors)/total_scraped*100:.1f}%)")
print(f"Unknown: {len(unknown)} ({len(unknown)/total_scraped*100:.1f}%)")

# Save all results
all_results_file = Path("output/jan2026_all_results.csv")
results_df.to_csv(all_results_file, index=False)
print(f"\nAll results saved to: {all_results_file}")

# Save OWNERS ONLY
owners_file = Path("output/jan2026_owners_only.csv")
owners.to_csv(owners_file, index=False)
print(f"OWNERS ONLY saved to: {owners_file} ({len(owners)} records)")

# Show owner samples
print("\n" + "=" * 60)
print("OWNER-BUILDER SAMPLES")
print("=" * 60)
for i, (idx, row) in enumerate(owners.head(10).iterrows()):
    print(f"\n{i+1}. {row['PermitNum']} | {row['OriginalAddress1']}")
    print(f"   Cost: ${row['EstProjectCost']:,.0f} | {row['Description'][:60]}...")
    print(f"   Work performer: {row['work_performer_text'][:80] if row['work_performer_text'] else 'N/A'}...")

print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
elapsed_total = time.time() - start_time
print(f"Total time: {elapsed_total/60:.1f} minutes")
print(f"\nFinal output: {owners_file}")
