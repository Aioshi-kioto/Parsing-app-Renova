"""
Daily Update Script - Ежедневная загрузка новых пермитов
Запуск: python daily_update.py

Можно добавить в Windows Task Scheduler или cron для автоматизации.
"""
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json

# Directories
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# State file - хранит дату последней загрузки
STATE_FILE = DATA_DIR / "last_update.json"

# API
DATASET_URL = "https://data.seattle.gov/resource/76t5-zqzr.json"


def load_state() -> dict:
    """Загрузка состояния (последняя дата обновления)"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_date": None, "total_processed": 0}


def save_state(state: dict):
    """Сохранение состояния"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_new_permits(since_date: str = None) -> pd.DataFrame:
    """
    Загрузка новых пермитов с указанной даты
    
    Args:
        since_date: Дата в формате YYYY-MM-DD. Если None, берём за последние 7 дней.
    """
    if since_date is None:
        # По умолчанию - последние 7 дней
        since_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    conditions = [
        f"applieddate >= '{since_date}'",
        "permitclass = 'Single Family/Duplex'",
        "contractorcompanyname IS NULL",  # Потенциальные owner-builders
        "estprojectcost >= 5000",
    ]
    
    where_clause = " AND ".join(conditions)
    
    params = {
        "$where": where_clause,
        "$limit": "50000",
        "$order": "applieddate DESC",
    }
    
    print(f"[*] Fetching permits since {since_date}...")
    
    with httpx.Client(timeout=120) as client:
        resp = client.get(DATASET_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    
    df = pd.DataFrame(data)
    print(f"[+] Fetched {len(df)} records")
    
    return df


def load_existing_permits() -> set:
    """Загрузка уже обработанных номеров пермитов"""
    master_file = OUTPUT_DIR / "master_owner_builders.csv"
    
    if master_file.exists():
        existing_df = pd.read_csv(master_file)
        if "permitnum" in existing_df.columns:
            return set(existing_df["permitnum"].astype(str))
    
    return set()


def save_to_master(df: pd.DataFrame):
    """Добавление новых записей в мастер-файл"""
    master_file = OUTPUT_DIR / "master_owner_builders.csv"
    
    if master_file.exists():
        existing_df = pd.read_csv(master_file)
        combined = pd.concat([existing_df, df], ignore_index=True)
        # Удаляем дубликаты
        combined.drop_duplicates(subset=["permitnum"], keep="last", inplace=True)
        combined.to_csv(master_file, index=False)
        print(f"[+] Master file updated: {len(combined)} total records")
    else:
        df.to_csv(master_file, index=False)
        print(f"[+] Master file created: {len(df)} records")


def daily_update():
    """Основная функция ежедневного обновления"""
    print("="*60)
    print(f"DAILY UPDATE - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)
    
    # Загружаем состояние
    state = load_state()
    last_date = state.get("last_date")
    
    if last_date:
        print(f"[*] Last update: {last_date}")
    else:
        print("[*] First run - fetching last 30 days")
        last_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Загружаем существующие пермиты
    existing_permits = load_existing_permits()
    print(f"[*] Existing permits in database: {len(existing_permits)}")
    
    # Загружаем новые данные
    new_df = fetch_new_permits(since_date=last_date)
    
    if new_df.empty:
        print("[*] No new permits found")
        return
    
    # Фильтруем только реально новые
    if "permitnum" in new_df.columns:
        new_df["permitnum"] = new_df["permitnum"].astype(str)
        truly_new = new_df[~new_df["permitnum"].isin(existing_permits)]
        print(f"[*] Truly new permits: {len(truly_new)}")
    else:
        truly_new = new_df
    
    if truly_new.empty:
        print("[*] All permits already processed")
    else:
        # Сохраняем новые записи
        save_to_master(truly_new)
        
        # Сохраняем дневной отчёт
        today = datetime.now().strftime("%Y%m%d")
        daily_file = OUTPUT_DIR / f"daily_update_{today}.csv"
        truly_new.to_csv(daily_file, index=False)
        print(f"[+] Daily report saved: {daily_file}")
        
        # Статистика
        if "estprojectcost" in truly_new.columns:
            truly_new["estprojectcost"] = pd.to_numeric(truly_new["estprojectcost"], errors="coerce")
            avg_cost = truly_new["estprojectcost"].mean()
            print(f"\n[*] New permits stats:")
            print(f"    - Count: {len(truly_new)}")
            print(f"    - Avg cost: ${avg_cost:,.0f}")
        
        # Примеры новых адресов
        if "originaladdress1" in truly_new.columns:
            print(f"\n[*] Sample new addresses:")
            for addr in truly_new["originaladdress1"].head(5):
                print(f"    - {addr}")
    
    # Обновляем состояние
    state["last_date"] = datetime.now().strftime("%Y-%m-%d")
    state["total_processed"] = len(existing_permits) + len(truly_new)
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    print(f"\n[+] State saved. Total processed: {state['total_processed']}")
    print("="*60)


if __name__ == "__main__":
    daily_update()
