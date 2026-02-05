"""
Конфигурация Seattle Owner-Builder Tracker
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
for dir_path in [DATA_DIR, OUTPUT_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Socrata API Settings
SOCRATA_CONFIG = {
    "domain": os.getenv("SOCRATA_DOMAIN", "data.seattle.gov"),
    "dataset_id": os.getenv("SOCRATA_DATASET_ID", "76t5-zqzr"),
    "app_token": os.getenv("SOCRATA_APP_TOKEN"),
}

# Accela Portal URLs
ACCELA_BASE_URL = "https://cosaccela.seattle.gov"
ACCELA_PERMIT_URL = f"{ACCELA_BASE_URL}/portal/cap/capDetail.aspx"

# Filters for API query
PERMIT_FILTERS = {
    "permit_class": ["Single Family / Duplex"],
    "permit_type_mapped": ["Building"],
    "year": 2026,
    "min_value": 5000,  # Минимальная стоимость работ
}

# Fields to remove from final output (25+ fields as per spec)
FIELDS_TO_REMOVE = [
    "link",
    "latitude",
    "longitude",
    "location",
    "permitclassmapped",
    "statuscurrent",
    "originalzip",
    "originalcity",
    "originalstate",
    "originaladdress1",
    "relatedmup",
    "housingunitscurrent",
    "housingunitsproposed",
    "housingunitsnettotal",
    "affordablehousingcurrent",
    "affordablehousingproposed",
    "affordablehousingnettotal",
    "housingunit",
    "relatedsdc",
    "masterpermitnum",
    "parentfoldernumber",
    "parentfolderapn",
    "parentfolderyn",
    "environmentallycrticalareas",
    "shoreline",
]

# Browser/Playwright Settings
BROWSER_CONFIG = {
    "headless": os.getenv("HEADLESS", "true").lower() == "true",
    "max_concurrent": int(os.getenv("MAX_CONCURRENT_BROWSERS", 3)),
    "request_delay_ms": int(os.getenv("REQUEST_DELAY_MS", 2000)),
    "timeout_ms": 30000,
    "viewport": {"width": 1920, "height": 1080},
}

# Proxy Settings
PROXY_CONFIG = {
    "url": os.getenv("PROXY_URL"),
    "username": os.getenv("PROXY_USERNAME"),
    "password": os.getenv("PROXY_PASSWORD"),
}

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Keywords for filtering
OWNER_KEYWORDS = ["owner", "property owner", "self"]
CONTRACTOR_KEYWORDS = ["licensed contractor", "contractor"]
