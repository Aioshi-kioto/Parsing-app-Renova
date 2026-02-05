"""Find the correct Seattle Building Permits dataset"""
import httpx

# Known Seattle building permit datasets
datasets = [
    ("76t5-zqzr", "Current dataset"),
    ("k44w-2dcq", "Building Permits dataset 1"),
    ("6nqv-y8x9", "Building Permits dataset 2"),
    ("uyyd-8gak", "Issued building permits"),
    ("mags-97de", "Building permits - 2024"),
]

print("Searching for correct Seattle Building Permits dataset...\n")

for dataset_id, name in datasets:
    url = f"https://data.seattle.gov/resource/{dataset_id}.json"
    params = {"$limit": "5"}
    
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    cols = list(data[0].keys())
                    has_applieddate = "applieddate" in cols
                    has_permitclass = "permitclass" in cols
                    has_contractor = "contractorcompanyname" in cols
                    
                    print(f"[+] {dataset_id} - {name}")
                    print(f"    Records: {len(data)}")
                    print(f"    Has applieddate: {has_applieddate}")
                    print(f"    Has permitclass: {has_permitclass}")
                    print(f"    Has contractor: {has_contractor}")
                    print(f"    Columns: {cols[:10]}...")
                    print()
                else:
                    print(f"[-] {dataset_id} - Empty")
            else:
                print(f"[-] {dataset_id} - HTTP {resp.status_code}")
    except Exception as e:
        print(f"[-] {dataset_id} - Error: {e}")

# Try to find building permits via search
print("\n" + "="*60)
print("Trying alternate building permits endpoint...")

# Seattle official building permits dataset
url = "https://data.seattle.gov/resource/uyyd-8gak.json"
params = {"$limit": "10", "$order": "applieddate DESC"}

try:
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        data = resp.json()
        
        if data:
            print(f"\nFound {len(data)} records")
            print(f"Columns: {list(data[0].keys())}")
            
            if "applieddate" in data[0]:
                print(f"Latest applieddate: {data[0].get('applieddate')}")
            if "permitclass" in data[0]:
                print(f"Permit class: {data[0].get('permitclass')}")
except Exception as e:
    print(f"Error: {e}")
