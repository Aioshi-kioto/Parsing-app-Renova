"""SQLite database setup and migrations"""
import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "zillow.db"


def init_database():
    """Initialize SQLite database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Таблица parse_jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parse_jobs (
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
    
    # Таблица homes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS homes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            zpid TEXT NOT NULL,
            address TEXT,
            city TEXT,
            state TEXT,
            zipcode TEXT,
            price REAL,
            beds INTEGER,
            baths REAL,
            area_sqft INTEGER,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES parse_jobs(id),
            UNIQUE(zpid)
        )
    """)
    
    # Индексы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_homes_job_id ON homes(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_homes_zpid ON homes(zpid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON parse_jobs(status)")
    
    conn.commit()
    conn.close()


def get_connection():
    """Get database connection"""
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def dict_factory(cursor, row):
    """Convert row to dict"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
