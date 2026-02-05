"""
Обработка и очистка данных пермитов
"""
import pandas as pd
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from loguru import logger

import sys
sys.path.append('..')
from config import FIELDS_TO_REMOVE, OUTPUT_DIR


class DataProcessor:
    """Класс для обработки и очистки данных пермитов"""
    
    def __init__(self, df: Optional[pd.DataFrame] = None):
        self.df = df
        self.processed_df = None
        
    def load_csv(self, filepath: Path) -> pd.DataFrame:
        """Загрузка данных из CSV"""
        self.df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(self.df)} records from {filepath}")
        return self.df
    
    def remove_fields(self, fields: Optional[List[str]] = None) -> pd.DataFrame:
        """Удаление ненужных полей из датафрейма"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        fields_to_remove = fields or FIELDS_TO_REMOVE
        
        # Находим поля, которые реально существуют в данных
        existing_fields = [f for f in fields_to_remove if f in self.df.columns]
        
        self.processed_df = self.df.drop(columns=existing_fields, errors='ignore')
        
        logger.info(f"Removed {len(existing_fields)} fields: {existing_fields}")
        logger.info(f"Remaining fields: {self.processed_df.columns.tolist()}")
        
        return self.processed_df
    
    def filter_owner_builders(self, owner_status_column: str = "owner_builder_status") -> pd.DataFrame:
        """Фильтрация только записей со статусом Owner"""
        if self.processed_df is None:
            self.processed_df = self.df
            
        if owner_status_column in self.processed_df.columns:
            self.processed_df = self.processed_df[
                self.processed_df[owner_status_column].str.lower().str.contains("owner", na=False)
            ]
            logger.info(f"Filtered to {len(self.processed_df)} owner-builder records")
        
        return self.processed_df
    
    def add_verification_status(self) -> pd.DataFrame:
        """Добавление колонки для статуса верификации"""
        if self.processed_df is None:
            self.processed_df = self.df.copy()
            
        self.processed_df["verification_status"] = "pending"
        self.processed_df["verified_at"] = None
        self.processed_df["owner_name"] = None
        self.processed_df["owner_address"] = None
        
        return self.processed_df
    
    def save_csv(self, filename: Optional[str] = None) -> Path:
        """Сохранение результатов в CSV"""
        if self.processed_df is None:
            raise ValueError("No processed data to save")
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"owner_builders_{timestamp}.csv"
        
        filepath = OUTPUT_DIR / filename
        self.processed_df.to_csv(filepath, index=False)
        
        logger.info(f"Saved {len(self.processed_df)} records to {filepath}")
        return filepath
    
    def get_stats(self) -> dict:
        """Получение статистики по данным"""
        df = self.processed_df if self.processed_df is not None else self.df
        
        if df is None:
            return {}
        
        stats = {
            "total_records": len(df),
            "columns": df.columns.tolist(),
            "date_range": None,
            "permit_classes": None,
            "avg_project_cost": None,
        }
        
        if "applieddate" in df.columns:
            stats["date_range"] = {
                "min": df["applieddate"].min(),
                "max": df["applieddate"].max(),
            }
        
        if "permitclass" in df.columns:
            stats["permit_classes"] = df["permitclass"].value_counts().to_dict()
        
        if "estprojectcost" in df.columns:
            df["estprojectcost"] = pd.to_numeric(df["estprojectcost"], errors='coerce')
            stats["avg_project_cost"] = df["estprojectcost"].mean()
        
        return stats
    
    def analyze_contractors(self) -> dict:
        """Анализ данных о контракторах"""
        df = self.df
        
        if df is None:
            return {}
        
        analysis = {
            "total_permits": len(df),
            "no_contractor": 0,
            "has_contractor": 0,
            "contractor_distribution": {},
        }
        
        if "contractorcompanyname" in df.columns:
            no_contractor = df["contractorcompanyname"].isna().sum()
            analysis["no_contractor"] = int(no_contractor)
            analysis["has_contractor"] = len(df) - int(no_contractor)
            
            # Топ контракторов
            top_contractors = df["contractorcompanyname"].value_counts().head(10)
            analysis["contractor_distribution"] = top_contractors.to_dict()
        
        return analysis


# Для быстрого тестирования
if __name__ == "__main__":
    processor = DataProcessor()
    # Тест загрузки
    # processor.load_csv(Path("../data/raw_permits.csv"))
    # stats = processor.get_stats()
    # print(stats)
