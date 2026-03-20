"""
Dashboard Operations API
Unified endpoint for the Operations Terminal dashboard.
"""
from fastapi import APIRouter

try:
    from backend.database import get_connection, dict_factory
except ImportError:
    from database import get_connection, dict_factory

router = APIRouter()


@router.get("/operations")
async def get_operations():
    """Aggregated operations data for Dashboard."""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    active_jobs = 0
    total_leads = 0
    leads_last_week = 0
    outbound_today = 0
    errors_24h = 0
    recent_alerts = []
    batchdata_used = 0
    batchdata_limit = 0  # Pay-as-you-go, лимит не фиксирован

    try:
        # Active jobs (running/parsing/verifying across all job tables)
        for tbl in ["zillow_jobs", "permit_jobs", "mbp_jobs"]:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {tbl} WHERE status IN ('running', 'parsing', 'verifying', 'pending')")
                row = cursor.fetchone()
                if row:
                    active_jobs += row["cnt"]
            except Exception:
                pass

        # Total leads
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM leads")
            row = cursor.fetchone()
            if row:
                total_leads = row["cnt"]
        except Exception:
            pass

        # Leads last week
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM leads WHERE found_at >= NOW() - INTERVAL '7 days'")
            row = cursor.fetchone()
            if row:
                leads_last_week = row["cnt"]
        except Exception:
            pass

        # Outbound today (letter_sent or email_sent today)
        try:
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM leads 
                WHERE (sent_lob_at >= CURRENT_DATE OR sent_apollo_at >= CURRENT_DATE)
            """)
            row = cursor.fetchone()
            if row:
                outbound_today = row["cnt"]
        except Exception:
            pass

        # Errors 24h (failed jobs)
        for tbl in ["zillow_jobs", "permit_jobs", "mbp_jobs"]:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {tbl} WHERE status = 'failed' AND started_at >= NOW() - INTERVAL '24 hours'")
                row = cursor.fetchone()
                if row:
                    errors_24h += row["cnt"]
            except Exception:
                pass

    except Exception:
        pass
    finally:
        conn.close()

    return {
        "active_jobs": active_jobs,
        "total_leads": total_leads,
        "leads_last_week": leads_last_week,
        "outbound_today": outbound_today,
        "errors_24h": errors_24h,
        "recent_alerts": recent_alerts,
        "batchdata_used": batchdata_used,
        "batchdata_limit": batchdata_limit,
    }
