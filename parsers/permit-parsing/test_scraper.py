"""
Test scraper - filter Jan 2026 data and test Playwright on 5 links.
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import asyncio
import json

# ============================================================
# STEP 1: Filter data by January 2026
# ============================================================

print("=" * 60)
print("STEP 1: Filter data by January 2026")
print("=" * 60)

# Read the Excel file
excel_path = Path("output/seattle_permits_review_20260129_0219.xlsx")
df = pd.read_excel(excel_path, sheet_name="Owner-Builder Candidates")

print(f"Total records: {len(df)}")
print(f"Columns: {list(df.columns)}")

# Convert AppliedDate to datetime
df["AppliedDate"] = pd.to_datetime(df["AppliedDate"])

# Filter January 2026
jan_2026 = df[(df["AppliedDate"] >= "2026-01-01") & (df["AppliedDate"] < "2026-02-01")]
print(f"January 2026 records: {len(jan_2026)}")

# Save filtered data
filtered_file = Path("output/jan_2026_candidates.csv")
jan_2026.to_csv(filtered_file, index=False)
print(f"Saved to: {filtered_file}")

# Show sample
print("\nSample records:")
for i, row in jan_2026.head(5).iterrows():
    print(f"  {row['PermitNum']} | {row['AppliedDate'].date()} | {row['OriginalAddress1']}")

# ============================================================
# STEP 2: Extract 5 links for testing
# ============================================================

print("\n" + "=" * 60)
print("STEP 2: Extract 5 test links")
print("=" * 60)

# Get 5 permit numbers for testing
test_permits = jan_2026.head(5)["PermitNum"].tolist()
print(f"Test permits: {test_permits}")

# Extract link URLs from the Link column
# The Link column contains dict-like string: "{'url': 'https://...'}"
def extract_url(link_str):
    if pd.isna(link_str):
        return None
    try:
        if isinstance(link_str, str):
            # Parse the dict-like string
            link_dict = eval(link_str)
            return link_dict.get("url")
        elif isinstance(link_str, dict):
            return link_str.get("url")
    except:
        return None
    return None

test_links = []
for permitnum in test_permits:
    row = jan_2026[jan_2026["PermitNum"] == permitnum].iloc[0]
    url = extract_url(row["Link"])
    test_links.append({
        "permitnum": permitnum,
        "url": url,
        "address": row["OriginalAddress1"],
    })
    print(f"  {permitnum}: {url}")

# ============================================================
# STEP 3: Check Playwright installation
# ============================================================

print("\n" + "=" * 60)
print("STEP 3: Check Playwright installation")
print("=" * 60)

try:
    from playwright.sync_api import sync_playwright
    print("[OK] Playwright imported successfully")
    PLAYWRIGHT_OK = True
except ImportError as e:
    print(f"[ERROR] Playwright not installed: {e}")
    PLAYWRIGHT_OK = False

try:
    from playwright_stealth import stealth_sync
    print("[OK] playwright-stealth imported successfully")
    STEALTH_OK = True
except ImportError as e:
    print(f"[WARN] playwright-stealth not installed: {e}")
    STEALTH_OK = False

# ============================================================
# STEP 4: Test scraping on 5 links
# ============================================================

print("\n" + "=" * 60)
print("STEP 4: Test scraping on 5 links")
print("=" * 60)

results = []

if PLAYWRIGHT_OK:
    with sync_playwright() as p:
        print("Launching browser (headless=True)...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        
        for i, item in enumerate(test_links):
            permitnum = item["permitnum"]
            url = item["url"]
            address = item["address"]
            
            print(f"\n--- Test {i+1}/5: {permitnum} ---")
            print(f"URL: {url}")
            print(f"Address: {address}")
            
            result = {
                "permitnum": permitnum,
                "url": url,
                "address": address,
                "status": None,
                "page_title": None,
                "page_loaded": False,
                "contractor_disclosure_found": False,
                "work_performer_text": None,
                "is_owner_builder": None,
                "error": None,
                "html_snippet": None,
            }
            
            if not url:
                result["error"] = "No URL found"
                results.append(result)
                print(f"  [SKIP] No URL")
                continue
            
            try:
                page = context.new_page()
                
                # Apply stealth if available
                if STEALTH_OK:
                    stealth_sync(page)
                
                # Navigate
                print(f"  Navigating...")
                response = page.goto(url, timeout=30000, wait_until="networkidle")
                
                result["status"] = response.status if response else None
                result["page_title"] = page.title()
                result["page_loaded"] = response.status == 200 if response else False
                
                print(f"  Status: {result['status']}")
                print(f"  Title: {result['page_title']}")
                
                # Wait for content
                page.wait_for_timeout(2000)
                
                # Get full page text for analysis
                page_text = page.inner_text("body")
                
                # Save HTML snippet for analysis
                html_content = page.content()
                result["html_snippet"] = html_content[:5000]  # First 5000 chars
                
                # Look for Contractor Disclosure section
                disclosure_keywords = [
                    "Who will be performing all the work",
                    "Contractor Disclosure",
                    "work performer",
                    "owner",
                    "licensed contractor",
                ]
                
                found_keywords = []
                for kw in disclosure_keywords:
                    if kw.lower() in page_text.lower():
                        found_keywords.append(kw)
                
                result["contractor_disclosure_found"] = len(found_keywords) > 0
                print(f"  Found keywords: {found_keywords}")
                
                # Try to find the specific field
                if "Who will be performing" in page_text:
                    # Extract surrounding text
                    idx = page_text.lower().find("who will be performing")
                    snippet = page_text[max(0, idx-50):idx+200]
                    result["work_performer_text"] = snippet.strip()
                    print(f"  Work performer text: {snippet[:100]}...")
                    
                    # Determine owner/contractor
                    snippet_lower = snippet.lower()
                    if "owner" in snippet_lower and "licensed contractor" not in snippet_lower:
                        result["is_owner_builder"] = True
                    elif "licensed contractor" in snippet_lower:
                        result["is_owner_builder"] = False
                    else:
                        result["is_owner_builder"] = None
                
                # Check for protection/blocking
                if "access denied" in page_text.lower() or "blocked" in page_text.lower():
                    result["error"] = "Access denied/blocked"
                    print(f"  [WARN] Access denied or blocked!")
                
                if "captcha" in page_text.lower() or "robot" in page_text.lower():
                    result["error"] = "Captcha/bot detection"
                    print(f"  [WARN] Captcha or bot detection!")
                
                page.close()
                
            except Exception as e:
                result["error"] = str(e)
                print(f"  [ERROR] {e}")
            
            results.append(result)
            print(f"  is_owner_builder: {result['is_owner_builder']}")
        
        browser.close()

# ============================================================
# STEP 5: Save results
# ============================================================

print("\n" + "=" * 60)
print("STEP 5: Results Summary")
print("=" * 60)

# Save detailed results
results_file = Path("output/scraper_test_results.json")
with open(results_file, "w", encoding="utf-8") as f:
    # Remove html_snippet for readability
    results_clean = []
    for r in results:
        r_clean = {k: v for k, v in r.items() if k != "html_snippet"}
        results_clean.append(r_clean)
    json.dump(results_clean, f, indent=2, ensure_ascii=False, default=str)
print(f"Detailed results saved to: {results_file}")

# Summary table
print("\nTest Results:")
print("-" * 80)
print(f"{'PermitNum':<15} {'Status':<8} {'Loaded':<8} {'Disclosure':<12} {'Owner?':<10} {'Error'}")
print("-" * 80)

for r in results:
    status = r.get("status", "-")
    loaded = "Yes" if r.get("page_loaded") else "No"
    disclosure = "Yes" if r.get("contractor_disclosure_found") else "No"
    owner = {True: "OWNER", False: "CONTRACTOR", None: "UNKNOWN"}.get(r.get("is_owner_builder"), "-")
    error = r.get("error", "-") or "-"
    error = error[:20] + "..." if len(str(error)) > 20 else error
    print(f"{r['permitnum']:<15} {status!s:<8} {loaded:<8} {disclosure:<12} {owner:<10} {error}")

print("-" * 80)

# Stats
total = len(results)
loaded = sum(1 for r in results if r.get("page_loaded"))
disclosure_found = sum(1 for r in results if r.get("contractor_disclosure_found"))
owners = sum(1 for r in results if r.get("is_owner_builder") is True)
contractors = sum(1 for r in results if r.get("is_owner_builder") is False)
unknown = sum(1 for r in results if r.get("is_owner_builder") is None)
errors = sum(1 for r in results if r.get("error"))

print(f"\nStats:")
print(f"  Total tests: {total}")
print(f"  Pages loaded: {loaded}")
print(f"  Disclosure found: {disclosure_found}")
print(f"  Owners: {owners}")
print(f"  Contractors: {contractors}")
print(f"  Unknown: {unknown}")
print(f"  Errors: {errors}")

# Save HTML snippets for manual review
snippets_dir = Path("output/html_snippets")
snippets_dir.mkdir(exist_ok=True)
for r in results:
    if r.get("html_snippet"):
        snippet_file = snippets_dir / f"{r['permitnum']}.html"
        with open(snippet_file, "w", encoding="utf-8") as f:
            f.write(r["html_snippet"])
print(f"\nHTML snippets saved to: {snippets_dir}/")
