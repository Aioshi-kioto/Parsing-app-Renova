"""
Клиент для работы с Socrata SODA API (data.seattle.gov)
Получение первичных метаданных о пермитах
"""
import httpx
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

import sys
sys.path.append('..')
from config import SOCRATA_CONFIG, PERMIT_FILTERS


class SeattlePermitsAPI:
    """Клиент для Seattle Open Data API (Socrata)"""
    
    def __init__(self, app_token: Optional[str] = None):
        self.domain = SOCRATA_CONFIG["domain"]
        self.dataset_id = SOCRATA_CONFIG["dataset_id"]
        self.app_token = app_token or SOCRATA_CONFIG["app_token"]
        self.base_url = f"https://{self.domain}/resource/{self.dataset_id}.json"
        
    def _build_query(
        self,
        year: int = 2026,
        permit_class: Optional[List[str]] = None,
        permit_type: Optional[str] = None,
        contractor_is_null: bool = True,
        min_value: int = 5000,
        limit: int = 10000,
        offset: int = 0,
    ) -> Dict[str, str]:
        """Построение SoQL запроса для фильтрации пермитов"""
        
        conditions = []
        
        # Фильтр по году
        conditions.append(f"applieddate >= '{year}-01-01'")
        conditions.append(f"applieddate < '{year + 1}-01-01'")
        
        # Фильтр по классу пермита
        if permit_class:
            classes = ", ".join([f"'{c}'" for c in permit_class])
            conditions.append(f"permitclass in ({classes})")
        
        # Фильтр по типу пермита
        if permit_type:
            conditions.append(f"permittypemapped = '{permit_type}'")
        
        # Фильтр: контрактор не указан (потенциальный self-builder)
        if contractor_is_null:
            conditions.append("contractorcompanyname IS NULL")
        
        # Фильтр по минимальной стоимости работ
        if min_value:
            conditions.append(f"estprojectcost >= {min_value}")
        
        where_clause = " AND ".join(conditions)
        
        params = {
            "$where": where_clause,
            "$limit": str(limit),
            "$offset": str(offset),
            "$order": "applieddate DESC",
        }
        
        if self.app_token:
            params["$$app_token"] = self.app_token
            
        return params
    
    async def fetch_permits(
        self,
        year: int = 2026,
        contractor_is_null: bool = True,
        limit: int = 10000,
    ) -> pd.DataFrame:
        """
        Получение списка пермитов с фильтрацией
        
        Args:
            year: Год для фильтрации
            contractor_is_null: Фильтр по отсутствию контрактора
            limit: Максимальное количество записей
            
        Returns:
            DataFrame с данными пермитов
        """
        params = self._build_query(
            year=year,
            permit_class=PERMIT_FILTERS["permit_class"],
            permit_type=PERMIT_FILTERS["permit_type_mapped"],
            contractor_is_null=contractor_is_null,
            min_value=PERMIT_FILTERS["min_value"],
            limit=limit,
        )
        
        logger.info(f"Fetching permits from {self.base_url}")
        logger.debug(f"Query params: {params}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        df = pd.DataFrame(data)
        logger.info(f"Fetched {len(df)} permits")
        
        return df
    
    def fetch_permits_sync(
        self,
        year: int = 2026,
        contractor_is_null: bool = True,
        limit: int = 10000,
    ) -> pd.DataFrame:
        """Синхронная версия fetch_permits"""
        params = self._build_query(
            year=year,
            permit_class=PERMIT_FILTERS["permit_class"],
            permit_type=PERMIT_FILTERS["permit_type_mapped"],
            contractor_is_null=contractor_is_null,
            min_value=PERMIT_FILTERS["min_value"],
            limit=limit,
        )
        
        logger.info(f"Fetching permits from {self.base_url}")
        
        with httpx.Client(timeout=60.0) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        df = pd.DataFrame(data)
        logger.info(f"Fetched {len(df)} permits")
        
        return df
    
    def get_permit_by_id(self, permit_num: str) -> Optional[Dict[str, Any]]:
        """Получение информации о конкретном пермите по номеру"""
        params = {
            "$where": f"permitnum = '{permit_num}'",
            "$limit": "1",
        }
        
        if self.app_token:
            params["$$app_token"] = self.app_token
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        return data[0] if data else None


# Для быстрого тестирования
if __name__ == "__main__":
    import asyncio
    
    async def test():
        api = SeattlePermitsAPI()
        df = await api.fetch_permits(year=2026, limit=100)
        print(df.head())
        print(f"\nColumns: {df.columns.tolist()}")
        print(f"\nTotal records: {len(df)}")
    
    asyncio.run(test())
