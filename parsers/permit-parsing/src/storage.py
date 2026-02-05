"""
Хранилище данных: CSV и PostgreSQL
"""
import pandas as pd
from pathlib import Path
from typing import Optional, List, Set
from datetime import datetime
from loguru import logger

import sys
sys.path.append('..')
from config import DATA_DIR, OUTPUT_DIR, DATABASE_URL

try:
    from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Float, Text
    from sqlalchemy.orm import sessionmaker, declarative_base
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class CSVStorage:
    """Хранилище на базе CSV файлов"""
    
    def __init__(self, processed_file: str = "processed_permits.csv"):
        self.processed_file = DATA_DIR / processed_file
        self._processed_ids: Set[str] = set()
        self._load_processed_ids()
    
    def _load_processed_ids(self) -> None:
        """Загрузка уже обработанных ID пермитов"""
        if self.processed_file.exists():
            df = pd.read_csv(self.processed_file)
            if "permitnum" in df.columns:
                self._processed_ids = set(df["permitnum"].astype(str))
            logger.info(f"Loaded {len(self._processed_ids)} processed permit IDs")
    
    def is_processed(self, permit_num: str) -> bool:
        """Проверка, был ли пермит уже обработан"""
        return str(permit_num) in self._processed_ids
    
    def filter_new_permits(self, df: pd.DataFrame, id_column: str = "permitnum") -> pd.DataFrame:
        """Фильтрация только новых (необработанных) пермитов"""
        if id_column not in df.columns:
            return df
        
        mask = ~df[id_column].astype(str).isin(self._processed_ids)
        new_df = df[mask]
        
        logger.info(f"Filtered {len(df)} -> {len(new_df)} new permits")
        return new_df
    
    def mark_processed(self, df: pd.DataFrame, id_column: str = "permitnum") -> None:
        """Пометка пермитов как обработанных"""
        if id_column in df.columns:
            new_ids = set(df[id_column].astype(str))
            self._processed_ids.update(new_ids)
        
        # Добавляем к существующему файлу
        if self.processed_file.exists():
            existing_df = pd.read_csv(self.processed_file)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.drop_duplicates(subset=[id_column], keep='last', inplace=True)
            combined_df.to_csv(self.processed_file, index=False)
        else:
            df.to_csv(self.processed_file, index=False)
        
        logger.info(f"Marked {len(df)} permits as processed")
    
    def save_owner_builders(self, df: pd.DataFrame, filename: Optional[str] = None) -> Path:
        """Сохранение найденных owner-builders"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"owner_builders_{timestamp}.csv"
        
        filepath = OUTPUT_DIR / filename
        
        # Если файл существует, добавляем к нему
        if filepath.exists():
            existing_df = pd.read_csv(filepath)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            if "permitnum" in combined_df.columns:
                combined_df.drop_duplicates(subset=["permitnum"], keep='last', inplace=True)
            combined_df.to_csv(filepath, index=False)
            logger.info(f"Appended to {filepath}, total: {len(combined_df)} records")
        else:
            df.to_csv(filepath, index=False)
            logger.info(f"Saved {len(df)} owner-builders to {filepath}")
        
        return filepath
    
    def get_processed_count(self) -> int:
        """Получение количества обработанных пермитов"""
        return len(self._processed_ids)


class PostgreSQLStorage:
    """Хранилище на базе PostgreSQL (опционально)"""
    
    def __init__(self, database_url: Optional[str] = None):
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("SQLAlchemy required. Install with: pip install sqlalchemy psycopg2-binary")
        
        self.database_url = database_url or DATABASE_URL
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")
        
        self.engine = create_engine(self.database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Создаем таблицы
        Base = declarative_base()
        
        class Permit(Base):
            __tablename__ = 'permits'
            
            permitnum = Column(String, primary_key=True)
            address = Column(String)
            permitclass = Column(String)
            estprojectcost = Column(Float)
            applieddate = Column(DateTime)
            is_owner_builder = Column(Boolean, default=False)
            verified = Column(Boolean, default=False)
            verified_at = Column(DateTime)
            owner_name = Column(String)
            owner_address = Column(String)
            raw_data = Column(Text)
        
        Base.metadata.create_all(self.engine)
        self.Permit = Permit
        
        logger.info("PostgreSQL storage initialized")
    
    def save_permits(self, df: pd.DataFrame) -> None:
        """Сохранение пермитов в БД"""
        df.to_sql('permits', self.engine, if_exists='append', index=False)
        logger.info(f"Saved {len(df)} permits to database")
    
    def get_unverified_permits(self, limit: int = 100) -> List[str]:
        """Получение списка непроверенных пермитов"""
        session = self.Session()
        try:
            permits = session.query(self.Permit.permitnum).filter(
                self.Permit.verified == False
            ).limit(limit).all()
            return [p[0] for p in permits]
        finally:
            session.close()
    
    def update_verification_status(
        self,
        permit_num: str,
        is_owner_builder: bool,
        owner_name: Optional[str] = None,
        owner_address: Optional[str] = None
    ) -> None:
        """Обновление статуса верификации пермита"""
        session = self.Session()
        try:
            permit = session.query(self.Permit).filter(
                self.Permit.permitnum == permit_num
            ).first()
            
            if permit:
                permit.verified = True
                permit.verified_at = datetime.now()
                permit.is_owner_builder = is_owner_builder
                permit.owner_name = owner_name
                permit.owner_address = owner_address
                session.commit()
        finally:
            session.close()


# Фабрика для выбора хранилища
def get_storage(use_postgres: bool = False):
    """Получение экземпляра хранилища"""
    if use_postgres and DATABASE_URL:
        return PostgreSQLStorage()
    return CSVStorage()
