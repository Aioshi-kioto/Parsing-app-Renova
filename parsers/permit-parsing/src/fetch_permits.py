"""
fetch_permits.py — Модуль загрузки данных из Seattle Open Data API

Реализует инкрементальную загрузку пермитов согласно docs/master_spec.md
"""
import httpx
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import json

# Конфигурация
SOCRATA_DOMAIN = "data.seattle.gov"
DATASET_ID = "76t5-zqzr"
BASE_URL = f"https://{SOCRATA_DOMAIN}/resource/{DATASET_ID}.json"

# Бизнес-фильтры (согласно master_spec.md раздел 3.3)
DEFAULT_FILTERS = {
    "permit_class": "Single Family/Duplex",
    "permit_type": "Building",
    "min_cost": 5000,
    "contractor_is_null": True,
}


class PermitFetcher:
    """
    Клиент для загрузки пермитов из Seattle Open Data API.
    
    Использует SODA API с SoQL запросами для инкрементальной
    загрузки только новых записей.
    """
    
    def __init__(self, app_token: Optional[str] = None):
        """
        Args:
            app_token: Socrata API токен (опционально, увеличивает rate limit)
        """
        self.app_token = app_token
        self.base_url = BASE_URL
    
    def build_soql_query(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        permit_class: str = DEFAULT_FILTERS["permit_class"],
        permit_type: str = DEFAULT_FILTERS["permit_type"],
        min_cost: int = DEFAULT_FILTERS["min_cost"],
        contractor_is_null: bool = DEFAULT_FILTERS["contractor_is_null"],
    ) -> str:
        """
        Построение SoQL WHERE условия согласно master_spec.md раздел 3.3
        
        Args:
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата (опционально, по умолчанию - сегодня)
            permit_class: Класс пермита
            permit_type: Тип пермита
            min_cost: Минимальная стоимость проекта
            contractor_is_null: Фильтр по отсутствию контрактора
            
        Returns:
            SoQL WHERE clause
        """
        conditions = []
        
        # Фильтр по дате подачи
        conditions.append(f"applieddate >= '{start_date}'")
        if end_date:
            conditions.append(f"applieddate < '{end_date}'")
        
        # Класс пермита
        conditions.append(f"permitclass = '{permit_class}'")
        
        # Тип пермита
        conditions.append(f"permittypemapped = '{permit_type}'")
        
        # Минимальная стоимость
        conditions.append(f"estprojectcost > {min_cost}")
        
        # Контрактор не указан
        if contractor_is_null:
            conditions.append("contractorcompanyname IS NULL")
        
        return " AND ".join(conditions)
    
    def fetch(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 10000,
        **filter_kwargs
    ) -> pd.DataFrame:
        """
        Загрузка пермитов за указанный период.
        
        Args:
            start_date: Начальная дата (YYYY-MM-DD)
            end_date: Конечная дата (опционально)
            limit: Максимум записей
            **filter_kwargs: Дополнительные параметры для build_soql_query
            
        Returns:
            DataFrame с пермитами
        """
        where_clause = self.build_soql_query(start_date, end_date, **filter_kwargs)
        
        params = {
            "$where": where_clause,
            "$limit": str(limit),
            "$order": "applieddate DESC",
        }
        
        if self.app_token:
            params["$$app_token"] = self.app_token
        
        print(f"[FETCH] Querying API...")
        print(f"[FETCH] WHERE: {where_clause[:100]}...")
        
        with httpx.Client(timeout=120.0) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        df = pd.DataFrame(data)
        print(f"[FETCH] Retrieved {len(df)} records")
        
        return df
    
    def fetch_incremental(
        self,
        last_run_date: Optional[str] = None,
        lookback_days: int = 7,
        **kwargs
    ) -> pd.DataFrame:
        """
        Инкрементальная загрузка с даты последнего запуска.
        
        Args:
            last_run_date: Дата последнего запуска (YYYY-MM-DD)
            lookback_days: Период по умолчанию если last_run_date не указан
            
        Returns:
            DataFrame с новыми пермитами
        """
        if last_run_date:
            start_date = last_run_date
        else:
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"[FETCH] Incremental load: {start_date} -> {end_date}")
        
        return self.fetch(start_date=start_date, end_date=end_date, **kwargs)


def deduplicate_permits(
    new_df: pd.DataFrame,
    existing_permits: set,
    key_column: str = "permitnum"
) -> pd.DataFrame:
    """
    Удаление дубликатов относительно уже сохранённых записей.
    
    Args:
        new_df: DataFrame с новыми данными
        existing_permits: Множество уже обработанных permitnum
        key_column: Колонка-ключ для сравнения
        
    Returns:
        DataFrame только с новыми записями
    """
    if key_column not in new_df.columns:
        return new_df
    
    new_df[key_column] = new_df[key_column].astype(str)
    mask = ~new_df[key_column].isin(existing_permits)
    
    result = new_df[mask].copy()
    print(f"[DEDUP] {len(new_df)} -> {len(result)} (removed {len(new_df) - len(result)} duplicates)")
    
    return result


def load_existing_permit_ids(master_file: Path) -> set:
    """
    Загрузка ID уже обработанных пермитов из master файла.
    
    Args:
        master_file: Путь к master_owner_builders.csv
        
    Returns:
        Множество permitnum
    """
    if not master_file.exists():
        return set()
    
    df = pd.read_csv(master_file)
    if "permitnum" in df.columns:
        return set(df["permitnum"].astype(str))
    
    return set()


# CLI интерфейс
if __name__ == "__main__":
    import sys
    
    fetcher = PermitFetcher()
    
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    else:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    df = fetcher.fetch(start_date=start_date)
    
    print(f"\nResults:")
    print(f"  Records: {len(df)}")
    if len(df) > 0:
        print(f"  Columns: {list(df.columns)[:5]}...")
        print(f"\nSample addresses:")
        for addr in df["originaladdress1"].head(5):
            print(f"    - {addr}")
