"""
Единая база данных для Renova Parse CRM
Sprint 2.5: Переведено с sqlite3 на SQLAlchemy + PostgreSQL.
Роутеры продолжают использовать тот же API (get_connection, dict_factory).
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy import text

try:
    from backend.database_setup import SessionLocal, engine, init_sqlalchemy_database
except Exception:
    from database_setup import SessionLocal, engine, init_sqlalchemy_database

logger = logging.getLogger(__name__)


# =======================================
# СОВМЕСТИМЫЙ API (drop-in для роутеров)
# =======================================

class _Cursor:
    """Обёртка над SQLAlchemy session, совместимая с sqlite3.Cursor API."""

    def __init__(self, session, row_factory=None):
        self._session = session
        self._result = None
        self._rows = []
        self._description = None
        self.rowcount = 0
        self._row_factory = row_factory

    @property
    def description(self):
        return self._description

    def execute(self, sql, params=None):
        # Заменяем sqlite3-плейсхолдеры `?` на SQLAlchemy `:pN`
        if params:
            indexed_sql = sql
            _params = {}
            idx = 0
            while '?' in indexed_sql:
                indexed_sql = indexed_sql.replace('?', f':p{idx}', 1)
                _params[f'p{idx}'] = params[idx]
                idx += 1
            self._result = self._session.execute(text(indexed_sql), _params)
        else:
            self._result = self._session.execute(text(sql))

        if self._result.returns_rows:
            self._description = [(col,) for col in self._result.keys()]
            raw_rows = self._result.fetchall()
            self.rowcount = len(raw_rows)
            if self._row_factory:
                self._rows = [self._row_factory(self, tuple(r)) for r in raw_rows]
            else:
                self._rows = [tuple(r) for r in raw_rows]
        else:
            self.rowcount = self._result.rowcount
            self._rows = []
            self._description = None

    def fetchone(self):
        if self._rows:
            return self._rows.pop(0)
        return None

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows

    @property
    def lastrowid(self):
        if self._result and hasattr(self._result, 'lastrowid'):
            return self._result.lastrowid
        # Для PostgreSQL используем RETURNING
        return None


class _ConnectionWrapper:
    """Обёртка над SQLAlchemy Session, совместимая с sqlite3.Connection API."""

    def __init__(self):
        self._session = SessionLocal()
        self.row_factory = None

    def cursor(self):
        return _Cursor(self._session, row_factory=self.row_factory)

    def commit(self):
        self._session.commit()

    def close(self):
        self._session.close()

    def execute(self, sql, params=None):
        c = self.cursor()
        c.execute(sql, params)
        return c


def get_connection():
    """Получить соединение с БД (drop-in замена sqlite3.connect)."""
    return _ConnectionWrapper()


def dict_factory(cursor, row):
    """Конвертировать строку в словарь (совместимость с sqlite3 row_factory)."""
    if cursor.description:
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    return {}


def init_database():
    """Инициализация базы данных — создание таблиц через SQLAlchemy ORM."""
    init_sqlalchemy_database()
    logger.info("Database initialized via SQLAlchemy.")


# ===============================
# ZILLOW ОПЕРАЦИИ
# ===============================

def create_zillow_job(urls: List[str]) -> int:
    """Создать задачу парсинга Zillow."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO zillow_jobs (urls, total_urls, status)
        VALUES (?, ?, 'pending')
        RETURNING id
    """, (json.dumps(urls), len(urls)))
    row = cursor.fetchone()
    job_id = row[0] if row else None
    conn.commit()
    conn.close()
    return job_id


def update_zillow_job(job_id: int, **kwargs):
    """Обновить задачу парсинга Zillow."""
    if not kwargs:
        return
    conn = get_connection()
    cursor = conn.cursor()

    set_parts = []
    params = []
    for key, value in kwargs.items():
        set_parts.append(f"{key} = ?")
        params.append(value)
    params.append(job_id)

    cursor.execute(f"""
        UPDATE zillow_jobs SET {', '.join(set_parts)} WHERE id = ?
    """, params)
    conn.commit()
    conn.close()


def insert_zillow_home(job_id: int, home_data: Dict[str, Any]) -> bool:
    """Вставить дом Zillow (игнорировать дубликаты по zpid)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        has_img = home_data.get('has_image')
        if isinstance(has_img, bool):
            has_img = 1 if has_img else 0

        cursor.execute("""
            INSERT INTO zillow_homes
            (job_id, zpid, address, city, state, zipcode, price, price_formatted, beds, baths,
             area_sqft, lot_size, year_built, home_type, latitude, longitude,
             date_sold, sold_date_text, zestimate, tax_assessed_value, has_image, detail_url, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zpid) DO NOTHING
        """, (
            job_id,
            home_data.get('zpid'),
            home_data.get('address'),
            home_data.get('city'),
            home_data.get('state'),
            home_data.get('zipcode'),
            home_data.get('price'),
            home_data.get('price_formatted'),
            home_data.get('beds'),
            home_data.get('baths'),
            home_data.get('area_sqft'),
            home_data.get('lot_size'),
            home_data.get('year_built'),
            home_data.get('home_type'),
            home_data.get('latitude'),
            home_data.get('longitude'),
            home_data.get('date_sold'),
            home_data.get('sold_date_text'),
            home_data.get('zestimate'),
            home_data.get('tax_assessed_value'),
            has_img,
            home_data.get('detail_url'),
            json.dumps(home_data.get('raw_data', {})) if home_data.get('raw_data') else None
        ))
        inserted = cursor.rowcount > 0
        conn.commit()
        return inserted
    except Exception as e:
        logger.error("Error inserting home: %s", e)
        return False
    finally:
        conn.close()


# ===============================
# PERMIT ОПЕРАЦИИ
# ===============================

def create_permit_job(year: int, permit_class: str = None, min_cost: float = 5000) -> int:
    """Создать задачу парсинга пермитов."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO permit_jobs (year, permit_class_filter, min_cost, status)
        VALUES (?, ?, ?, 'pending')
        RETURNING id
    """, (year, permit_class, min_cost))
    row = cursor.fetchone()
    job_id = row[0] if row else None
    conn.commit()
    conn.close()
    return job_id


def update_permit_job(job_id: int, **kwargs):
    """Обновить задачу парсинга пермитов."""
    if not kwargs:
        return
    conn = get_connection()
    cursor = conn.cursor()

    set_parts = []
    params = []
    for key, value in kwargs.items():
        set_parts.append(f"{key} = ?")
        params.append(value)
    params.append(job_id)

    cursor.execute(f"""
        UPDATE permit_jobs SET {', '.join(set_parts)} WHERE id = ?
    """, params)
    conn.commit()
    conn.close()


def insert_permit(job_id: int, permit_data: Dict[str, Any]) -> bool:
    """Вставить пермит (обновить если существует)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO permits
            (job_id, permit_num, permit_class, permit_class_mapped, permit_type_mapped,
             permit_type_desc, description, est_project_cost, applied_date, issued_date,
             status_current, address, city, state, zipcode, contractor_name,
             is_owner_builder, verification_status, work_performer_text, portal_link,
             latitude, longitude, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(permit_num) DO UPDATE SET
                job_id = EXCLUDED.job_id,
                is_owner_builder = EXCLUDED.is_owner_builder,
                verification_status = EXCLUDED.verification_status,
                work_performer_text = EXCLUDED.work_performer_text,
                updated_at = NOW()
        """, (
            job_id,
            permit_data.get('permit_num'),
            permit_data.get('permit_class'),
            permit_data.get('permit_class_mapped'),
            permit_data.get('permit_type_mapped'),
            permit_data.get('permit_type_desc'),
            permit_data.get('description'),
            permit_data.get('est_project_cost'),
            permit_data.get('applied_date'),
            permit_data.get('issued_date'),
            permit_data.get('status_current'),
            permit_data.get('address'),
            permit_data.get('city'),
            permit_data.get('state'),
            permit_data.get('zipcode'),
            permit_data.get('contractor_name'),
            permit_data.get('is_owner_builder'),
            permit_data.get('verification_status', 'pending'),
            permit_data.get('work_performer_text'),
            permit_data.get('portal_link'),
            permit_data.get('latitude'),
            permit_data.get('longitude'),
            json.dumps(permit_data.get('raw_data', {})) if permit_data.get('raw_data') else None
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error inserting permit: %s", e)
        return False
    finally:
        conn.close()


def update_permit_verification(permit_num: str, is_owner_builder: Optional[bool],
                               work_performer_text: str = None,
                               verification_error: str = None,
                               contacts_text: str = None):
    """Обновить статус верификации пермита."""
    conn = get_connection()
    cursor = conn.cursor()

    if verification_error:
        verification_status = 'error'
        work_performer_text = (verification_error[:500] if verification_error else None)
    else:
        verification_status = 'verified' if is_owner_builder is not None else 'unknown'

    contacts_val = (contacts_text[:2000] if contacts_text and len(contacts_text) > 2000 else contacts_text) if contacts_text else None

    cursor.execute("""
        UPDATE permits SET
            is_owner_builder = ?,
            verification_status = ?,
            work_performer_text = ?,
            contacts_text = ?,
            updated_at = NOW()
        WHERE permit_num = ?
    """, (
        True if is_owner_builder else (False if is_owner_builder is False else None),
        verification_status,
        work_performer_text,
        contacts_val,
        permit_num
    ))
    conn.commit()
    conn.close()


# ===============================
# MYBUILDINGPERMIT ОПЕРАЦИИ
# ===============================

def create_mbp_job(jurisdictions: List[str], days_back: int = 30) -> int:
    """Создать задачу парсинга MyBuildingPermit."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mbp_jobs (jurisdictions, days_back, status)
        VALUES (?, ?, 'pending')
        RETURNING id
    """, (json.dumps(jurisdictions), days_back))
    row = cursor.fetchone()
    job_id = row[0] if row else None
    conn.commit()
    conn.close()
    return job_id


def update_mbp_job(job_id: int, **kwargs):
    """Обновить задачу парсинга MyBuildingPermit."""
    if not kwargs:
        return
    conn = get_connection()
    cursor = conn.cursor()

    set_parts = []
    params = []
    for key, value in kwargs.items():
        set_parts.append(f"{key} = ?")
        params.append(value)
    params.append(job_id)

    cursor.execute(f"""
        UPDATE mbp_jobs SET {', '.join(set_parts)} WHERE id = ?
    """, params)
    conn.commit()
    conn.close()


def insert_mbp_permit(job_id: int, permit_data: Dict[str, Any]) -> bool:
    """Вставить пермит MyBuildingPermit (обновить если существует)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO mbp_permits
            (job_id, permit_number, jurisdiction, project_name, description,
             permit_type, permit_status, address, parcel, applied_date, issued_date,
             applicant_name, contractor_name, contractor_license, is_owner_builder, matches_target_type, permit_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(permit_number, jurisdiction) DO UPDATE SET
                job_id = EXCLUDED.job_id,
                project_name = EXCLUDED.project_name,
                permit_status = EXCLUDED.permit_status,
                is_owner_builder = EXCLUDED.is_owner_builder,
                matches_target_type = EXCLUDED.matches_target_type
        """, (
            job_id,
            permit_data.get('permit_number'),
            permit_data.get('jurisdiction'),
            permit_data.get('project_name'),
            permit_data.get('description'),
            permit_data.get('permit_type'),
            permit_data.get('permit_status'),
            permit_data.get('address'),
            permit_data.get('parcel'),
            permit_data.get('applied_date'),
            permit_data.get('issued_date'),
            permit_data.get('applicant_name'),
            permit_data.get('contractor_name'),
            permit_data.get('contractor_license'),
            True if permit_data.get('is_owner_builder') else False,
            True if permit_data.get('matches_target_type') else False,
            permit_data.get('permit_url')
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error("Error inserting MBP permit: %s", e)
        return False
    finally:
        conn.close()


# ===============================
# СТАТИСТИКА
# ===============================

def get_overview_stats() -> Dict[str, Any]:
    """Получить общую статистику для Dashboard."""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    try:
        # Zillow
        cursor.execute("SELECT COUNT(*) as cnt FROM zillow_homes")
        total_homes = cursor.fetchone().get("cnt", 0) if cursor.fetchone is not None else 0
        # Re-query since fetchone consumed it
        cursor.execute("SELECT COUNT(*) as cnt FROM zillow_homes")
        total_homes = (cursor.fetchone() or {}).get("cnt", 0)

        cursor.execute("SELECT COUNT(DISTINCT zpid) as cnt FROM zillow_homes")
        unique_homes = (cursor.fetchone() or {}).get("cnt", 0)

        cursor.execute("SELECT AVG(price) as avg FROM zillow_homes WHERE price IS NOT NULL")
        avg_home_price = (cursor.fetchone() or {}).get("avg", 0) or 0

        # Permits
        cursor.execute("SELECT COUNT(*) as cnt FROM permits")
        total_permits = (cursor.fetchone() or {}).get("cnt", 0)

        cursor.execute("SELECT COUNT(*) as cnt FROM permits WHERE is_owner_builder = true")
        owner_builders = (cursor.fetchone() or {}).get("cnt", 0)

        cursor.execute("SELECT SUM(est_project_cost) as total FROM permits WHERE est_project_cost IS NOT NULL")
        total_project_cost = (cursor.fetchone() or {}).get("total", 0) or 0

        # MBP
        cursor.execute("SELECT COUNT(*) as cnt FROM mbp_permits")
        mbp_total_permits = (cursor.fetchone() or {}).get("cnt", 0)

        cursor.execute("SELECT COUNT(*) as cnt FROM mbp_permits WHERE is_owner_builder = true")
        mbp_owner_builders = (cursor.fetchone() or {}).get("cnt", 0)

        # Recent jobs
        cursor.execute("""
            (SELECT 'zillow' as type, id, status, started_at FROM zillow_jobs ORDER BY started_at DESC LIMIT 2)
            UNION ALL
            (SELECT 'permit' as type, id, status, started_at FROM permit_jobs ORDER BY started_at DESC LIMIT 2)
            UNION ALL
            (SELECT 'mbp' as type, id, status, started_at FROM mbp_jobs ORDER BY started_at DESC LIMIT 2)
            ORDER BY started_at DESC LIMIT 5
        """)
        recent_jobs = cursor.fetchall()

        conn.close()

        return {
            "zillow": {
                "total_homes": total_homes,
                "unique_homes": unique_homes,
                "avg_price": round(float(avg_home_price), 2)
            },
            "permits": {
                "total_permits": total_permits,
                "owner_builders": owner_builders,
                "total_project_cost": round(float(total_project_cost), 2)
            },
            "mbp": {
                "total_permits": mbp_total_permits,
                "owner_builders": mbp_owner_builders
            },
            "recent_jobs": [
                {"type": r.get("type"), "id": r.get("id"), "status": r.get("status"), "started_at": str(r.get("started_at")) if r.get("started_at") else None}
                for r in recent_jobs
            ] if recent_jobs else []
        }
    except Exception as e:
        logger.error("Error getting overview stats: %s", e)
        conn.close()
        return {
            "zillow": {"total_homes": 0, "unique_homes": 0, "avg_price": 0},
            "permits": {"total_permits": 0, "owner_builders": 0, "total_project_cost": 0},
            "mbp": {"total_permits": 0, "owner_builders": 0},
            "recent_jobs": []
        }


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!")
