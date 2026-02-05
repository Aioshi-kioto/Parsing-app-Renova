"""
Скрипт для загрузки и первичного анализа данных пермитов Сиэтла
Запуск: python download_and_analyze.py
"""
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime

# Создаём папки
DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Настройки API
SOCRATA_DOMAIN = "data.seattle.gov"
DATASET_ID = "76t5-zqzr"  # Seattle Building Permits
BASE_URL = f"https://{SOCRATA_DOMAIN}/resource/{DATASET_ID}.json"


def fetch_permits(
    year: int = 2026,
    permit_classes: list = None,
    contractor_is_null: bool = True,
    min_value: int = 5000,
    limit: int = 50000
) -> pd.DataFrame:
    """
    Загрузка пермитов с фильтрацией
    """
    if permit_classes is None:
        permit_classes = ["Single Family / Duplex"]
    
    # Строим SoQL запрос
    conditions = [
        f"applieddate >= '{year}-01-01'",
        f"applieddate < '{year + 1}-01-01'",
    ]
    
    # Фильтр по классу
    if permit_classes:
        classes = ", ".join([f"'{c}'" for c in permit_classes])
        conditions.append(f"permitclass in ({classes})")
    
    # Фильтр по типу
    conditions.append("permittypemapped = 'Building'")
    
    # Фильтр: контрактор не указан
    if contractor_is_null:
        conditions.append("contractorcompanyname IS NULL")
    
    # Минимальная стоимость
    if min_value:
        conditions.append(f"estprojectcost >= {min_value}")
    
    where_clause = " AND ".join(conditions)
    
    params = {
        "$where": where_clause,
        "$limit": str(limit),
        "$order": "applieddate DESC",
    }
    
    print(f"Fetching permits from Seattle Open Data...")
    print(f"URL: {BASE_URL}")
    print(f"Filter: {where_clause[:100]}...")
    
    with httpx.Client(timeout=120.0) as client:
        response = client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
    
    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} records")
    
    return df


def analyze_data(df: pd.DataFrame) -> dict:
    """
    Анализ загруженных данных
    """
    print(f"\n{'='*70}")
    print("SEATTLE PERMITS DATA ANALYSIS")
    print(f"{'='*70}")
    
    print(f"\n[*] Total records: {len(df)}")
    print(f"[*] Columns: {len(df.columns)}")
    
    # Список колонок
    print(f"\n[*] Available fields ({len(df.columns)}):")
    for i, col in enumerate(sorted(df.columns), 1):
        print(f"  {i:2}. {col}")
    
    stats = {"total": len(df), "columns": df.columns.tolist()}
    
    # Даты
    if "applieddate" in df.columns:
        df["applieddate"] = pd.to_datetime(df["applieddate"])
        print(f"\n[*] Date range: {df['applieddate'].min().date()} - {df['applieddate'].max().date()}")
        stats["date_min"] = str(df["applieddate"].min().date())
        stats["date_max"] = str(df["applieddate"].max().date())
    
    # Классы пермитов
    if "permitclass" in df.columns:
        print(f"\n[*] Permit classes:")
        for cls, count in df["permitclass"].value_counts().items():
            print(f"  - {cls}: {count}")
        stats["permit_classes"] = df["permitclass"].value_counts().to_dict()
    
    # Типы пермитов
    if "permittypemapped" in df.columns:
        print(f"\n[*] Permit types:")
        for typ, count in df["permittypemapped"].value_counts().head(10).items():
            print(f"  - {typ}: {count}")
    
    # Стоимость проектов
    if "estprojectcost" in df.columns:
        df["estprojectcost"] = pd.to_numeric(df["estprojectcost"], errors="coerce")
        avg_cost = df["estprojectcost"].mean()
        min_cost = df["estprojectcost"].min()
        max_cost = df["estprojectcost"].max()
        print(f"\n[*] Project costs:")
        print(f"  - Average: ${avg_cost:,.0f}")
        print(f"  - Min: ${min_cost:,.0f}")
        print(f"  - Max: ${max_cost:,.0f}")
        stats["avg_cost"] = avg_cost
    
    # Статус контрактора
    if "contractorcompanyname" in df.columns:
        no_contractor = df["contractorcompanyname"].isna().sum()
        has_contractor = len(df) - no_contractor
        print(f"\n[*] Contractors:")
        print(f"  - No contractor (potential self-builder): {no_contractor} ({no_contractor/len(df)*100:.1f}%)")
        print(f"  - Has contractor: {has_contractor}")
        stats["no_contractor"] = int(no_contractor)
    
    # Адреса
    if "originaladdress1" in df.columns:
        print(f"\n[*] Sample addresses (first 5):")
        for addr in df["originaladdress1"].head(5):
            print(f"  - {addr}")
    
    # Описание работ
    if "description" in df.columns:
        print(f"\n[*] Sample work descriptions (first 3):")
        for desc in df["description"].dropna().head(3):
            print(f"  - {desc[:100]}...")
    
    return stats


def save_data(df: pd.DataFrame, prefix: str = "permits") -> tuple:
    """
    Сохранение данных в CSV
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Полные данные
    raw_file = DATA_DIR / f"{prefix}_raw_{timestamp}.csv"
    df.to_csv(raw_file, index=False)
    print(f"\n[+] Raw data saved: {raw_file}")
    
    # Поля для удаления (по ТЗ)
    fields_to_remove = [
        "link", "latitude", "longitude", "location",
        "permitclassmapped", "statuscurrent", "originalzip",
        "originalcity", "originalstate", "relatedmup",
        "housingunitscurrent", "housingunitsproposed",
        "housingunitsnettotal", "affordablehousingcurrent",
        "affordablehousingproposed", "affordablehousingnettotal",
        "housingunit", "relatedsdc", "masterpermitnum",
        "parentfoldernumber", "parentfolderapn", "parentfolderyn",
        "environmentallycrticalareas", "shoreline",
    ]
    
    # Удаляем ненужные поля
    existing_fields = [f for f in fields_to_remove if f in df.columns]
    clean_df = df.drop(columns=existing_fields, errors="ignore")
    
    clean_file = OUTPUT_DIR / f"{prefix}_clean_{timestamp}.csv"
    clean_df.to_csv(clean_file, index=False)
    print(f"[+] Clean data saved: {clean_file}")
    print(f"    Removed fields: {len(existing_fields)}")
    print(f"    Remaining fields: {len(clean_df.columns)}")
    
    return raw_file, clean_file


def main():
    """Главная функция"""
    print("[*] Seattle Owner-Builder Tracker - Download\n")
    
    # Загружаем данные
    df = fetch_permits(
        year=2026,
        permit_classes=["Single Family / Duplex"],
        contractor_is_null=True,  # Потенциальные self-builders
        min_value=5000,
        limit=50000
    )
    
    if df.empty:
        print("[!] No data found")
        return
    
    # Анализируем
    stats = analyze_data(df)
    
    # Сохраняем
    raw_file, clean_file = save_data(df, "seattle_permits_2026")
    
    print(f"\n{'='*70}")
    print("[+] DONE!")
    print(f"{'='*70}")
    print(f"\nNext step: Playwright verification")
    print(f"Command: python main.py verify {clean_file}")


if __name__ == "__main__":
    main()
