"""
Analytics API Router
Endpoints для аналитики и визуализации данных
"""
from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_connection, dict_factory, get_overview_stats
from models import (
    OverviewStats, TimelineDataPoint, DistributionDataPoint,
    CityStats, MapMarker, MapDataResponse
)

router = APIRouter()


def _parse_price(val):
    """Парсит цену из int/float/str (в т.ч. '$999,880') в float"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace('$', '').replace(',', '').replace(' ', '').strip()
        if cleaned:
            try:
                return float(cleaned)
            except ValueError:
                pass
    return None


@router.get("/overview", response_model=OverviewStats)
async def get_overview():
    """Общая статистика для Dashboard"""
    stats = get_overview_stats()
    return OverviewStats(**stats)


# ===============================
# ZILLOW ANALYTICS
# ===============================

@router.get("/zillow/price-distribution", response_model=List[DistributionDataPoint])
async def zillow_price_distribution(
    job_id: Optional[int] = None,
    bins: int = Query(default=10, ge=5, le=20)
):
    """Распределение цен домов Zillow"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    
    # Получаем min/max цены
    cursor.execute(f"""
        SELECT MIN(price), MAX(price) FROM zillow_homes 
        WHERE price IS NOT NULL {job_filter}
    """)
    min_price, max_price = cursor.fetchone()
    
    min_price = _parse_price(min_price)
    max_price = _parse_price(max_price)
    if min_price is None or max_price is None:
        conn.close()
        return []
    
    # Создаём бины
    bin_size = (max_price - min_price) / bins
    result = []
    
    # Выражение для приведения price к числу (на случай TEXT со значением '$999,880')
    price_expr = "CAST(REPLACE(REPLACE(REPLACE(COALESCE(CAST(price AS TEXT), ''), '$', ''), ',', ''), ' ', '') AS REAL)"
    
    for i in range(bins):
        low = min_price + (i * bin_size)
        high = min_price + ((i + 1) * bin_size)
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM zillow_homes 
            WHERE price IS NOT NULL AND {price_expr} >= ? AND {price_expr} < ? {job_filter}
        """, (low, high))
        count = cursor.fetchone()[0]
        
        label = f"${int(low/1000)}K-${int(high/1000)}K"
        result.append(DistributionDataPoint(label=label, count=count))
    
    conn.close()
    return result


@router.get("/zillow/timeline", response_model=List[TimelineDataPoint])
async def zillow_timeline(
    days: int = Query(default=30, ge=7, le=365),
    job_id: Optional[int] = None
):
    """Динамика добавления домов Zillow по дням"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute(f"""
        SELECT date(created_at) as date, COUNT(*) as count, AVG(price) as avg_price
        FROM zillow_homes
        WHERE date(created_at) >= ? {job_filter}
        GROUP BY date(created_at)
        ORDER BY date(created_at)
    """, (start_date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        TimelineDataPoint(date=row[0], count=row[1], value=round(row[2], 2) if row[2] else None)
        for row in rows
    ]


@router.get("/zillow/by-city", response_model=List[CityStats])
async def zillow_by_city(
    limit: int = Query(default=10, ge=5, le=50),
    job_id: Optional[int] = None
):
    """Статистика Zillow по городам"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"""
        SELECT city, COUNT(*) as count, AVG(price) as avg_price, SUM(price) as total_value
        FROM zillow_homes
        WHERE city IS NOT NULL AND city != '' {job_filter}
        GROUP BY city
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        CityStats(
            city=row[0],
            count=row[1],
            avg_price=round(row[2], 2) if row[2] else None,
            total_value=round(row[3], 2) if row[3] else None
        )
        for row in rows
    ]


@router.get("/zillow/home-types", response_model=List[DistributionDataPoint])
async def zillow_home_types(job_id: Optional[int] = None):
    """Распределение по типам домов"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"""
        SELECT home_type, COUNT(*) as count
        FROM zillow_homes
        WHERE home_type IS NOT NULL {job_filter}
        GROUP BY home_type
        ORDER BY count DESC
    """)
    
    rows = cursor.fetchall()
    total = sum(row[1] for row in rows)
    conn.close()
    
    return [
        DistributionDataPoint(
            label=row[0] or "Unknown",
            count=row[1],
            percentage=round(row[1] / total * 100, 1) if total > 0 else 0
        )
        for row in rows
    ]


# ===============================
# PERMITS ANALYTICS
# ===============================

@router.get("/permits/cost-distribution", response_model=List[DistributionDataPoint])
async def permits_cost_distribution(
    job_id: Optional[int] = None,
    bins: int = Query(default=10, ge=5, le=20)
):
    """Распределение стоимости проектов"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"""
        SELECT MIN(est_project_cost), MAX(est_project_cost) FROM permits 
        WHERE est_project_cost IS NOT NULL {job_filter}
    """)
    min_cost, max_cost = cursor.fetchone()
    
    if not min_cost or not max_cost:
        conn.close()
        return []
    
    bin_size = (max_cost - min_cost) / bins
    result = []
    
    for i in range(bins):
        low = min_cost + (i * bin_size)
        high = min_cost + ((i + 1) * bin_size)
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM permits 
            WHERE est_project_cost >= ? AND est_project_cost < ? {job_filter}
        """, (low, high))
        count = cursor.fetchone()[0]
        
        label = f"${int(low/1000)}K-${int(high/1000)}K"
        result.append(DistributionDataPoint(label=label, count=count))
    
    conn.close()
    return result


@router.get("/permits/timeline", response_model=List[TimelineDataPoint])
async def permits_timeline(
    days: int = Query(default=90, ge=30, le=365),
    job_id: Optional[int] = None
):
    """Динамика пермитов по дням (applied_date)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute(f"""
        SELECT date(applied_date) as date, COUNT(*) as count, SUM(est_project_cost) as total_cost
        FROM permits
        WHERE date(applied_date) >= ? AND applied_date IS NOT NULL {job_filter}
        GROUP BY date(applied_date)
        ORDER BY date(applied_date)
    """, (start_date,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        TimelineDataPoint(date=row[0], count=row[1], value=round(row[2], 2) if row[2] else None)
        for row in rows
    ]


@router.get("/permits/owner-builder-ratio", response_model=List[DistributionDataPoint])
async def permits_owner_builder_ratio(job_id: Optional[int] = None):
    """Соотношение owner-builders vs contractors"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"WHERE job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"""
        SELECT 
            SUM(CASE WHEN is_owner_builder = 1 THEN 1 ELSE 0 END) as owners,
            SUM(CASE WHEN is_owner_builder = 0 THEN 1 ELSE 0 END) as contractors,
            SUM(CASE WHEN is_owner_builder IS NULL THEN 1 ELSE 0 END) as unknown
        FROM permits {job_filter}
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    owners = row[0] or 0
    contractors = row[1] or 0
    unknown = row[2] or 0
    total = owners + contractors + unknown
    
    if total == 0:
        return []
    
    return [
        DistributionDataPoint(
            label="Owner-Builder",
            count=owners,
            percentage=round(owners / total * 100, 1)
        ),
        DistributionDataPoint(
            label="Licensed Contractor",
            count=contractors,
            percentage=round(contractors / total * 100, 1)
        ),
        DistributionDataPoint(
            label="Unknown",
            count=unknown,
            percentage=round(unknown / total * 100, 1)
        )
    ]


@router.get("/permits/by-permit-class", response_model=List[DistributionDataPoint])
async def permits_by_class(job_id: Optional[int] = None):
    """Распределение по классам пермитов"""
    conn = get_connection()
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"""
        SELECT permit_class, COUNT(*) as count
        FROM permits
        WHERE permit_class IS NOT NULL {job_filter}
        GROUP BY permit_class
        ORDER BY count DESC
    """)
    
    rows = cursor.fetchall()
    total = sum(row[1] for row in rows)
    conn.close()
    
    return [
        DistributionDataPoint(
            label=row[0],
            count=row[1],
            percentage=round(row[1] / total * 100, 1) if total > 0 else 0
        )
        for row in rows
    ]


# ===============================
# MAP DATA
# ===============================

@router.get("/map/zillow", response_model=MapDataResponse)
async def map_zillow_homes(
    job_id: Optional[int] = None,
    limit: int = Query(default=500, ge=1, le=2000)
):
    """Данные для карты - дома Zillow"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    job_filter = f"AND job_id = {job_id}" if job_id else ""
    
    cursor.execute(f"""
        SELECT id, zpid, address, city, state, price, beds, baths, latitude, longitude
        FROM zillow_homes
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL {job_filter}
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return MapDataResponse(markers=[], center={"lat": 47.6062, "lng": -122.3321})
    
    markers = [
        MapMarker(
            id=row['id'],
            type="zillow",
            latitude=row['latitude'],
            longitude=row['longitude'],
            title=f"${row['price']:,.0f}" if row['price'] else "N/A",
            address=row['address'],
            price=row['price'],
            details={
                "zpid": row['zpid'],
                "city": row['city'],
                "state": row['state'],
                "beds": row['beds'],
                "baths": row['baths']
            }
        )
        for row in rows
    ]
    
    # Вычисляем центр
    avg_lat = sum(m.latitude for m in markers) / len(markers)
    avg_lng = sum(m.longitude for m in markers) / len(markers)
    
    return MapDataResponse(
        markers=markers,
        center={"lat": avg_lat, "lng": avg_lng}
    )


@router.get("/map/permits", response_model=MapDataResponse)
async def map_permits(
    job_id: Optional[int] = None,
    is_owner_builder: Optional[bool] = None,
    limit: int = Query(default=500, ge=1, le=2000)
):
    """Данные для карты - пермиты"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    conditions = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
    params = []
    
    if job_id:
        conditions.append("job_id = ?")
        params.append(job_id)
    if is_owner_builder is not None:
        conditions.append("is_owner_builder = ?")
        params.append(1 if is_owner_builder else 0)
    
    where = " AND ".join(conditions)
    
    cursor.execute(f"""
        SELECT id, permit_num, address, city, est_project_cost, 
               is_owner_builder, permit_class, latitude, longitude
        FROM permits
        WHERE {where}
        LIMIT ?
    """, params + [limit])
    
    rows = cursor.fetchall()
    conn.close()
    
    # Дефолтный центр - Seattle
    if not rows:
        return MapDataResponse(markers=[], center={"lat": 47.6062, "lng": -122.3321})
    
    markers = [
        MapMarker(
            id=row['id'],
            type="permit",
            latitude=row['latitude'],
            longitude=row['longitude'],
            title=row['permit_num'],
            address=row['address'],
            price=row['est_project_cost'],
            details={
                "permit_class": row['permit_class'],
                "city": row['city'],
                "is_owner_builder": bool(row['is_owner_builder']) if row['is_owner_builder'] is not None else None
            }
        )
        for row in rows
    ]
    
    avg_lat = sum(m.latitude for m in markers) / len(markers)
    avg_lng = sum(m.longitude for m in markers) / len(markers)
    
    return MapDataResponse(
        markers=markers,
        center={"lat": avg_lat, "lng": avg_lng}
    )


@router.get("/map/combined", response_model=MapDataResponse)
async def map_combined(
    limit: int = Query(default=500, ge=1, le=2000)
):
    """Данные для карты - комбинированные (Zillow + Permits)"""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    markers = []
    
    # Zillow homes
    cursor.execute("""
        SELECT id, zpid, address, city, price, latitude, longitude
        FROM zillow_homes
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT ?
    """, (limit // 2,))
    
    for row in cursor.fetchall():
        markers.append(MapMarker(
            id=row['id'],
            type="zillow",
            latitude=row['latitude'],
            longitude=row['longitude'],
            title=f"${row['price']:,.0f}" if row['price'] else "Zillow",
            address=row['address'],
            price=row['price']
        ))
    
    # Permits
    cursor.execute("""
        SELECT id, permit_num, address, est_project_cost, latitude, longitude
        FROM permits
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT ?
    """, (limit // 2,))
    
    for row in cursor.fetchall():
        markers.append(MapMarker(
            id=row['id'],
            type="permit",
            latitude=row['latitude'],
            longitude=row['longitude'],
            title=row['permit_num'],
            address=row['address'],
            price=row['est_project_cost']
        ))
    
    conn.close()
    
    if not markers:
        return MapDataResponse(markers=[], center={"lat": 47.6062, "lng": -122.3321})
    
    avg_lat = sum(m.latitude for m in markers) / len(markers)
    avg_lng = sum(m.longitude for m in markers) / len(markers)
    
    return MapDataResponse(
        markers=markers,
        center={"lat": avg_lat, "lng": avg_lng}
    )
