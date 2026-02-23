"""
Конфигурация MyBuildingPermit Parser
https://permitsearch.mybuildingpermit.com/

Сайт: ASP.NET, Kendo UI Grid, серверный рендеринг
Парсинг: Playwright (рекомендуется — ViewState, формы, Kendo UI)
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

for dir_path in [DATA_DIR, OUTPUT_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Base URL
BASE_URL = "https://permitsearch.mybuildingpermit.com"
SEARCH_URL = f"{BASE_URL}/"
# Детали: /PermitDetails/{PermitNumber}/{City}
PERMIT_DETAILS_URL = f"{BASE_URL}/PermitDetails"

# Jurisdictions (eCityGov Alliance) — только из TARGET_CONFIG (spec.md)
# Значения option value из HTML (для JS-установки в скрытом select)
JURISDICTION_VALUES = {
    "Auburn": "24",
    "Bellevue": "1",
    "Bothell": "2",
    "Burien": "11",
    "Edmonds": "23",
    "Kenmore": "4",
    "King County": "20",
    "Kirkland": "5",
    "Mercer Island": "6",
    "Mill Creek": "13",
    "Newcastle": "19",
    "Sammamish": "7",
    "Snoqualmie": "9",
}
JURISDICTIONS = [
    "Auburn",
    "Bellevue",
    "Bothell",
    "Burien",
    "Edmonds",
    "Kenmore",
    "King County",
    "Kirkland",
    "Mercer Island",
    "Mill Creek",
    "Newcastle",
    "Sammamish",
    "Snoqualmie",
]

# Form IDs / selectors (из анализа DOM)
FORM_ID = "permitSearchForm"
SEARCH_BUTTON_SELECTOR = "button[type='submit']"
# Результаты: Kendo UI Grid, классы k-master-row
RESULTS_GRID_SELECTOR = ".k-grid-content"
ROW_SELECTOR = ".k-master-row"

# DOM path для основного контента
CONTENT_SELECTOR = "section.main div.container.body-content div.row div.col-md-12"

# Полная конфигурация для парсинга пермитов (пост-фильтр по типу)
TARGET_CONFIG = {
    "Auburn": {
        "permit_types": ["ADDITION", "ALTERATIONS"],
        "date_range_days": 3,
    },
    "Bellevue": {
        "permit_types": ["WD", "BS", "BR", "DH"],
        "date_range_days": 3,
    },
    "Bothell": {
        "permit_types": ["BSF"],
        "date_range_days": 3,
    },
    "Burien": {
        "permit_types": ["Residential-Addition", "Residential - Remodel"],
        "date_range_days": 3,
    },
    "Edmonds": {
        "permit_types": [
            "SINGLE FAMILY-STRUCTURE ADDITION-ADDITION",
            "SINGLE FAMILY-REMODEL-ALTERATION",
        ],
        "date_range_days": 3,
    },
    "Kenmore": {
        "permit_types": ["SINGLE FAMILY"],
        "date_range_days": 3,
    },
    "King County": {
        "permit_types": ["Building/Residential Building/Addition-Improvement"],
        "date_range_days": 3,
    },
    "Kirkland": {
        "permit_types": ["ADU", "BSF"],
        "date_range_days": 3,
    },
    "Mercer Island": {
        "permit_types": ["Building"],
        "date_range_days": 3,
    },
    "Mill Creek": {
        "permit_types": ["Building"],
        "date_range_days": 3,
    },
    "Newcastle": {
        "permit_types": ["SINGLE FAMILY RESIDENCE"],
        "date_range_days": 3,
    },
    "Sammamish": {
        "permit_types": [
            "BLDG RESIDENTIAL - ADDITION",
            "BLDG RESIDENTIAL - ACCESSORY STRUCTURE",
            "BLDG RESIDENTIAL - REPAIR/DAMAGE",
            "BLDG RESIDENTIAL - REMODEL/ALTERATION",
        ],
        "date_range_days": 3,
    },
    "Snoqualmie": {
        "permit_types": ["Residential"],
        "date_range_days": 3,
    },
}

# Дополнительные настройки для адаптивного поиска
SEARCH_CONFIG = {
    "max_date_range": 7,
    "min_date_range": 1,
    "reduce_step": 1,
    "max_retries": 3,
    "page_load_timeout": 10000,
}

# Критерии фильтрации подрядчиков (People section)
CONTRACTOR_FILTER = {
    "empty_license": True,
    "owner_keywords": [
        "OWNER",
        "HOMEOWNER",
        "PROPERTY OWNER",
        "OWNER BUILDER",
        "OWNER-BUILDER",
    ],
    "exclude_with_license": True,
}

# Маппинг для типов в таблице People
PEOPLE_TYPES = {
    "applicant": "Applicant",
    "contractor": "Contractor",
    "owner": "Owner",
    "architect": "Architect",
    "engineer": "Engineer",
}

# Рекомендуемые фильтры для Owner-Builder (лиды)
# Permit Type и Permit Status зависят от Jurisdiction — уточнять по реальному DOM
OWNER_BUILDER_FILTERS = {
    "search_by": "Project Info",  # Permit #, Project Info, Location, People
    "date_type": "Applied",       # Applied, Issued, Finaled
    # Permit Type: jurisdiction-specific, примеры: Building, Single Family, Residential, New Construction
    "permit_types": ["Building", "Single Family", "Residential"],
    # Permit Status: jurisdiction-specific, примеры: Applied, In Review, Issued
    "permit_statuses": ["Applied", "In Review", "Issued"],
    # Пост-фильтр: Contractor = пусто (форма не поддерживает прямой поиск)
    "filter_no_contractor": True,
}

# Browser/Playwright
BROWSER_CONFIG = {
    "headless": os.getenv("HEADLESS", "true").lower() == "true",  # false = видимый браузер
    "timeout_ms": 30000,
    "viewport": {"width": 1920, "height": 1080},
    "request_delay_ms": int(os.getenv("REQUEST_DELAY_MS", 2000)),
}

# Test Mode
TEST_MODE_LIMIT = 3  # Лимит записей на город (2-3 для теста)
TEST_CITIES = JURISDICTIONS  # Все 15 городов

# Excel Export (сохранять в data/)
EXCEL_OUTPUT_DIR = DATA_DIR
EXCEL_FILENAME = "permits_mybuildingpermit.xlsx"

