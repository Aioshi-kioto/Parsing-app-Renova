"""Pydantic models for API"""
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


class ParseRequest(BaseModel):
    urls: List[str]


class ParseJobStatus(BaseModel):
    id: int
    status: str
    current_url_index: int
    total_urls: int
    homes_found: int
    unique_homes: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class Home(BaseModel):
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
    created_at: datetime


class JobListItem(BaseModel):
    id: int
    status: str
    total_urls: int
    homes_found: int
    unique_homes: int
    started_at: datetime
    completed_at: Optional[datetime] = None
