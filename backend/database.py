"""
Единая база данных для Renova Parse CRM
SQLite с таблицами для Zillow и Permits парсеров
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "renova_crm.db"


def init_database():
    """Инициализация базы данных со всеми таблицами"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # ===============================
    # ZILLOW ТАБЛИЦЫ
    # ===============================
    
    # Таблица zillow_jobs - задачи парсинга Zillow
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zillow_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urls TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            current_url_index INTEGER DEFAULT 0,
            total_urls INTEGER NOT NULL,
            homes_found INTEGER DEFAULT 0,
            unique_homes INTEGER DEFAULT 0,
            error_message TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)
    
    # Таблица zillow_homes - дома из Zillow
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zillow_homes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            zpid TEXT NOT NULL,
            address TEXT,
            city TEXT,
            state TEXT,
            zipcode TEXT,
            price REAL,
            price_formatted TEXT,
            beds INTEGER,
            baths REAL,
            area_sqft INTEGER,
            lot_size REAL,
            year_built INTEGER,
            home_type TEXT,
            latitude REAL,
            longitude REAL,
            date_sold TEXT,
            sold_date_text TEXT,
            zestimate REAL,
            tax_assessed_value REAL,
            has_image INTEGER,
            detail_url TEXT,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES zillow_jobs(id),
            UNIQUE(zpid)
        )
    """)
    
    # Миграция: добавить новые колонки если таблица уже существует
    for col, col_type in [
        ("price_formatted", "TEXT"),
        ("date_sold", "TEXT"),
        ("sold_date_text", "TEXT"),
        ("zestimate", "REAL"),
        ("tax_assessed_value", "REAL"),
        ("has_image", "INTEGER"),
        ("detail_url", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE zillow_homes ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # колонка уже есть
    
    # ===============================
    # PERMIT ТАБЛИЦЫ
    # ===============================
    
    # Таблица permit_jobs - задачи парсинга пермитов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permit_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'pending',
            year INTEGER NOT NULL,
            permit_class_filter TEXT,
            permit_type_filter TEXT,
            min_cost REAL DEFAULT 5000,
            permits_found INTEGER DEFAULT 0,
            permits_verified INTEGER DEFAULT 0,
            owner_builders_found INTEGER DEFAULT 0,
            error_message TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)
    
    # Таблица permits - строительные пермиты
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            permit_num TEXT NOT NULL,
            permit_class TEXT,
            permit_class_mapped TEXT,
            permit_type_mapped TEXT,
            permit_type_desc TEXT,
            description TEXT,
            est_project_cost REAL,
            applied_date DATE,
            issued_date DATE,
            status_current TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zipcode TEXT,
            contractor_name TEXT,
            is_owner_builder INTEGER DEFAULT NULL,
            verification_status TEXT DEFAULT 'pending',
            work_performer_text TEXT,
            portal_link TEXT,
            latitude REAL,
            longitude REAL,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES permit_jobs(id),
            UNIQUE(permit_num)
        )
    """)
    
    # ===============================
    # ИНДЕКСЫ
    # ===============================
    
    # Zillow индексы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zillow_homes_job_id ON zillow_homes(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zillow_homes_zpid ON zillow_homes(zpid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zillow_homes_city ON zillow_homes(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zillow_homes_price ON zillow_homes(price)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_zillow_jobs_status ON zillow_jobs(status)")
    
    # Permit индексы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_permits_job_id ON permits(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_permits_permit_num ON permits(permit_num)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_permits_applied_date ON permits(applied_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_permits_is_owner_builder ON permits(is_owner_builder)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_permits_city ON permits(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_permit_jobs_status ON permit_jobs(status)")
    
    # ===============================
    # MYBUILDINGPERMIT ТАБЛИЦЫ
    # ===============================
    
    # Таблица mbp_jobs - задачи парсинга MyBuildingPermit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mbp_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'pending',
            jurisdictions TEXT,
            days_back INTEGER DEFAULT 7,
            date_from_str TEXT,
            date_to_str TEXT,
            total_permits INTEGER DEFAULT 0,
            analyzed_count INTEGER DEFAULT 0,
            owner_builders_found INTEGER DEFAULT 0,
            elapsed_seconds REAL,
            current_jurisdiction TEXT,
            error_message TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)
    
    # Таблица mbp_permits - пермиты из MyBuildingPermit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mbp_permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            permit_number TEXT NOT NULL,
            jurisdiction TEXT,
            project_name TEXT,
            description TEXT,
            permit_type TEXT,
            permit_status TEXT,
            address TEXT,
            parcel TEXT,
            applied_date TEXT,
            issued_date TEXT,
            applicant_name TEXT,
            contractor_name TEXT,
            contractor_license TEXT,
            is_owner_builder INTEGER DEFAULT 0,
            matches_target_type INTEGER DEFAULT 0,
            permit_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES mbp_jobs(id),
            UNIQUE(permit_number, jurisdiction)
        )
    """)
    
    # Миграция mbp_jobs: новые колонки
    for col, col_type in [
        ("date_from_str", "TEXT"),
        ("date_to_str", "TEXT"),
        ("analyzed_count", "INTEGER"),
        ("elapsed_seconds", "REAL"),
        ("current_jurisdiction", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE mbp_jobs ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Миграция: matches_target_type в mbp_permits (для существующих БД)
    try:
        cursor.execute("ALTER TABLE mbp_permits ADD COLUMN matches_target_type INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # MyBuildingPermit индексы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mbp_permits_job_id ON mbp_permits(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mbp_permits_jurisdiction ON mbp_permits(jurisdiction)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mbp_permits_is_owner_builder ON mbp_permits(is_owner_builder)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mbp_jobs_status ON mbp_jobs(status)")
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DB_PATH}")


def get_connection():
    """Получить соединение с БД"""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def dict_factory(cursor, row):
    """Конвертировать строку в словарь"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# ===============================
# ZILLOW ОПЕРАЦИИ
# ===============================

def create_zillow_job(urls: List[str]) -> int:
    """Создать задачу парсинга Zillow"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO zillow_jobs (urls, total_urls, status)
        VALUES (?, ?, 'pending')
    """, (json.dumps(urls), len(urls)))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_zillow_job(job_id: int, **kwargs):
    """Обновить задачу парсинга Zillow"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        params.append(value)
    params.append(job_id)
    
    cursor.execute(f"""
        UPDATE zillow_jobs SET {', '.join(updates)} WHERE id = ?
    """, params)
    conn.commit()
    conn.close()


def insert_zillow_home(job_id: int, home_data: Dict[str, Any]) -> bool:
    """Вставить дом Zillow (игнорировать дубликаты по zpid)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        has_img = home_data.get('has_image')
        if isinstance(has_img, bool):
            has_img = 1 if has_img else 0
        cursor.execute("""
            INSERT OR IGNORE INTO zillow_homes 
            (job_id, zpid, address, city, state, zipcode, price, price_formatted, beds, baths, 
             area_sqft, lot_size, year_built, home_type, latitude, longitude,
             date_sold, sold_date_text, zestimate, tax_assessed_value, has_image, detail_url, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        print(f"Error inserting home: {e}")
        return False
    finally:
        conn.close()


# ===============================
# PERMIT ОПЕРАЦИИ
# ===============================

def create_permit_job(year: int, permit_class: str = None, min_cost: float = 5000) -> int:
    """Создать задачу парсинга пермитов"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO permit_jobs (year, permit_class_filter, min_cost, status)
        VALUES (?, ?, ?, 'pending')
    """, (year, permit_class, min_cost))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_permit_job(job_id: int, **kwargs):
    """Обновить задачу парсинга пермитов"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        params.append(value)
    params.append(job_id)
    
    cursor.execute(f"""
        UPDATE permit_jobs SET {', '.join(updates)} WHERE id = ?
    """, params)
    conn.commit()
    conn.close()


def insert_permit(job_id: int, permit_data: Dict[str, Any]) -> bool:
    """Вставить пермит (обновить если существует)"""
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
                job_id = excluded.job_id,
                is_owner_builder = excluded.is_owner_builder,
                verification_status = excluded.verification_status,
                work_performer_text = excluded.work_performer_text,
                updated_at = CURRENT_TIMESTAMP
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
        print(f"Error inserting permit: {e}")
        return False
    finally:
        conn.close()


def update_permit_verification(permit_num: str, is_owner_builder: Optional[bool], 
                               work_performer_text: str = None,
                               verification_error: str = None):
    """Обновить статус верификации пермита.
    verification_error: если верификация не выполнялась (например Playwright недоступен).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if verification_error:
        verification_status = 'error'
        work_performer_text = (verification_error[:500] if verification_error else None)
    else:
        verification_status = 'verified' if is_owner_builder is not None else 'unknown'
    
    cursor.execute("""
        UPDATE permits SET 
            is_owner_builder = ?,
            verification_status = ?,
            work_performer_text = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE permit_num = ?
    """, (
        1 if is_owner_builder else (0 if is_owner_builder is False else None),
        verification_status,
        work_performer_text,
        permit_num
    ))
    conn.commit()
    conn.close()


# ===============================
# MYBUILDINGPERMIT ОПЕРАЦИИ
# ===============================

def create_mbp_job(jurisdictions: List[str], days_back: int = 30) -> int:
    """Создать задачу парсинга MyBuildingPermit"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mbp_jobs (jurisdictions, days_back, status)
        VALUES (?, ?, 'pending')
    """, (json.dumps(jurisdictions), days_back))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_mbp_job(job_id: int, **kwargs):
    """Обновить задачу парсинга MyBuildingPermit"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        params.append(value)
    params.append(job_id)
    
    cursor.execute(f"""
        UPDATE mbp_jobs SET {', '.join(updates)} WHERE id = ?
    """, params)
    conn.commit()
    conn.close()


def insert_mbp_permit(job_id: int, permit_data: Dict[str, Any]) -> bool:
    """Вставить пермит MyBuildingPermit (обновить если существует)"""
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
                job_id = excluded.job_id,
                project_name = excluded.project_name,
                permit_status = excluded.permit_status,
                is_owner_builder = excluded.is_owner_builder,
                matches_target_type = excluded.matches_target_type
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
            1 if permit_data.get('is_owner_builder') else 0,
            1 if permit_data.get('matches_target_type') else 0,
            permit_data.get('permit_url')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting MBP permit: {e}")
        return False
    finally:
        conn.close()


# ===============================
# СТАТИСТИКА
# ===============================

def get_overview_stats() -> Dict[str, Any]:
    """Получить общую статистику для Dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Zillow статистика
    cursor.execute("SELECT COUNT(*) FROM zillow_homes")
    total_homes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT zpid) FROM zillow_homes")
    unique_homes = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(price) FROM zillow_homes WHERE price IS NOT NULL")
    avg_home_price = cursor.fetchone()[0] or 0
    
    # Permit статистика
    cursor.execute("SELECT COUNT(*) FROM permits")
    total_permits = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM permits WHERE is_owner_builder = 1")
    owner_builders = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(est_project_cost) FROM permits WHERE est_project_cost IS NOT NULL")
    total_project_cost = cursor.fetchone()[0] or 0
    
    # MBP статистика
    cursor.execute("SELECT COUNT(*) FROM mbp_permits")
    mbp_total_permits = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM mbp_permits WHERE is_owner_builder = 1")
    mbp_owner_builders = cursor.fetchone()[0]
    
    # Последние задачи
    cursor.execute("""
        SELECT 'zillow' as type, id, status, started_at FROM zillow_jobs
        UNION ALL
        SELECT 'permit' as type, id, status, started_at FROM permit_jobs
        UNION ALL
        SELECT 'mbp' as type, id, status, started_at FROM mbp_jobs
        ORDER BY started_at DESC LIMIT 5
    """)
    recent_jobs = cursor.fetchall()
    
    conn.close()
    
    return {
        "zillow": {
            "total_homes": total_homes,
            "unique_homes": unique_homes,
            "avg_price": round(avg_home_price, 2)
        },
        "permits": {
            "total_permits": total_permits,
            "owner_builders": owner_builders,
            "total_project_cost": round(total_project_cost, 2)
        },
        "mbp": {
            "total_permits": mbp_total_permits,
            "owner_builders": mbp_owner_builders
        },
        "recent_jobs": [
            {"type": r[0], "id": r[1], "status": r[2], "started_at": r[3]}
            for r in recent_jobs
        ]
    }


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!")
