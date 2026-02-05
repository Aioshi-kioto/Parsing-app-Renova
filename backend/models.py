"""
Pydantic модели для Renova Parse CRM API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum


# ===============================
# ОБЩИЕ МОДЕЛИ
# ===============================

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    ERROR = "error"


# ===============================
# ZILLOW МОДЕЛИ
# ===============================

class ZillowParseRequest(BaseModel):
    """Запрос на парсинг Zillow"""
    urls: List[str] = Field(..., min_length=1, description="Список URL для парсинга")


class ZillowJobStatus(BaseModel):
    """Статус задачи парсинга Zillow"""
    id: int
    status: str
    current_url_index: int = 0
    total_urls: int
    homes_found: int = 0
    unique_homes: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class ZillowJobListItem(BaseModel):
    """Элемент списка задач Zillow"""
    id: int
    status: str
    total_urls: int
    homes_found: int
    unique_homes: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class ZillowHome(BaseModel):
    """Дом из Zillow"""
    id: int
    job_id: int
    zpid: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    area_sqft: Optional[int] = None
    lot_size: Optional[int] = None
    year_built: Optional[int] = None
    home_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime


class ZillowHomesResponse(BaseModel):
    """Ответ со списком домов Zillow"""
    homes: List[ZillowHome]
    total: int


class ZillowStats(BaseModel):
    """Статистика Zillow"""
    total: int
    unique_count: int
    avg_price: float
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    avg_beds: float
    avg_baths: float
    avg_area_sqft: float


# ===============================
# PERMIT МОДЕЛИ
# ===============================

class PermitParseRequest(BaseModel):
    """Запрос на парсинг пермитов"""
    year: int = Field(default=2026, ge=2000, le=2030)
    month: Optional[int] = Field(default=None, ge=1, le=12, description="Месяц (1-12), если не задан — весь год")
    period: Optional[str] = Field(
        default=None,
        description="Период: last_month, last_3_months или year. Имеет приоритет над month"
    )
    permit_class: Optional[str] = Field(default="Single Family / Duplex")
    min_cost: float = Field(default=5000, ge=0)
    verify_owner_builder: bool = Field(default=True, description="Верифицировать owner-builder через портал")


class PermitJobStatus(BaseModel):
    """Статус задачи парсинга пермитов"""
    id: int
    status: str
    year: int
    permit_class_filter: Optional[str] = None
    min_cost: float
    permits_found: int = 0
    permits_verified: int = 0
    owner_builders_found: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class PermitJobListItem(BaseModel):
    """Элемент списка задач пермитов"""
    id: int
    status: str
    year: int
    permits_found: int
    owner_builders_found: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class Permit(BaseModel):
    """Строительный пермит"""
    id: int
    job_id: Optional[int] = None
    permit_num: str
    permit_class: Optional[str] = None
    permit_class_mapped: Optional[str] = None
    permit_type_mapped: Optional[str] = None
    permit_type_desc: Optional[str] = None
    description: Optional[str] = None
    est_project_cost: Optional[float] = None
    applied_date: Optional[str] = None
    issued_date: Optional[str] = None
    status_current: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    contractor_name: Optional[str] = None
    is_owner_builder: Optional[bool] = None
    verification_status: str = "pending"
    work_performer_text: Optional[str] = None
    portal_link: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PermitsResponse(BaseModel):
    """Ответ со списком пермитов"""
    permits: List[Permit]
    total: int


class PermitStats(BaseModel):
    """Статистика пермитов"""
    total: int
    owner_builders: int
    contractors: int
    unknown: int
    avg_cost: float
    min_cost: Optional[float] = None
    max_cost: Optional[float] = None
    total_cost: float


# ===============================
# ANALYTICS МОДЕЛИ
# ===============================

class OverviewStats(BaseModel):
    """Общая статистика для Dashboard"""
    zillow: dict
    permits: dict
    recent_jobs: List[dict]


class TimelineDataPoint(BaseModel):
    """Точка данных для графика временной динамики"""
    date: str
    count: int
    value: Optional[float] = None


class DistributionDataPoint(BaseModel):
    """Точка данных для распределения"""
    label: str
    count: int
    percentage: Optional[float] = None


class CityStats(BaseModel):
    """Статистика по городу"""
    city: str
    count: int
    avg_price: Optional[float] = None
    total_value: Optional[float] = None


class MapMarker(BaseModel):
    """Маркер для карты"""
    id: int
    type: str  # 'zillow' или 'permit'
    latitude: float
    longitude: float
    title: str
    address: Optional[str] = None
    price: Optional[float] = None
    details: Optional[dict] = None


class MapDataResponse(BaseModel):
    """Данные для карты"""
    markers: List[MapMarker]
    center: dict
    bounds: Optional[dict] = None
