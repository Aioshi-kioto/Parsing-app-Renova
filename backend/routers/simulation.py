"""
Simulation API Router
E2E testing: creates fake parser jobs, runs records through rules_engine,
creates real leads, mocks outbound, sends Telegram notifications.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

try:
    from backend.database import get_connection, dict_factory
    from backend.services.rules_engine import classify_lead
    from backend.services.lead_pipeline import ingest_record_to_leads
except ImportError:
    from database import get_connection, dict_factory
    from services.rules_engine import classify_lead
    from services.lead_pipeline import ingest_record_to_leads

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory simulation state
_simulations = {}


class SimulationRequest(BaseModel):
    delay_seconds: int = 5
    scenarios: List[str] = ["permit_sniper", "emergency_plumbing", "heloc", "sales", "escrow"]


class SimulationStatus(BaseModel):
    sim_id: str
    status: str
    progress: int
    created_leads: int
    log: List[str]


# Template records that will trigger specific rules_engine cases
TEMPLATE_RECORDS = {
    "permit_sniper": [
        {
            "permit_number": f"SIM-PS-{i}",
            "address": addr,
            "city": "Seattle",
            "state": "WA",
            "zip": "98103",
            "description": desc,
            "permit_class": "Structural",
            "permit_type": "Construction",
            "project_cost": cost,
            "applied_date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "issued_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "status": "Issued",
            "contractor_name": contractor,
            "is_owner_builder": False,
        }
        for i, (addr, desc, cost, contractor) in enumerate([
            ("1234 NE 65th St, Seattle, WA 98115", "Structural framing for addition per architect plans", 85000, "Pacific NW Builders"),
            ("567 Greenwood Ave N, Seattle, WA 98103", "Foundation and structural repair per engineer report", 120000, "Emerald City Construction"),
            ("890 Ballard Ave NW, Seattle, WA 98107", "Structural beam replacement per architectural drawings", 65000, "Cascade Structural LLC"),
        ], start=1)
    ],
    "emergency_plumbing": [
        {
            "permit_number": f"SIM-EP-{i}",
            "address": addr,
            "city": "Seattle",
            "state": "WA",
            "zip": "98117",
            "description": desc,
            "permit_class": "Plumbing",
            "permit_type": "Plumbing",
            "project_cost": cost,
            "applied_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "issued_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "status": "Issued",
            "contractor_name": contractor,
            "is_owner_builder": False,
        }
        for i, (addr, desc, cost, contractor) in enumerate([
            ("2345 NW 80th St, Seattle, WA 98117", "Emergency sewer line repair and replacement", 15000, "24/7 Plumbing Emergency"),
            ("678 N 85th St, Seattle, WA 98103", "Emergency water heater replacement burst pipe", 8000, "Roto-Rooter Services"),
        ], start=1)
    ],
    "heloc": [
        {
            "address": "4567 Lake City Way NE, Seattle, WA 98105",
            "city": "Seattle",
            "state": "WA",
            "zip": "98105",
            "sim_id": "SIM-HELOC-1",
            "property_value": 950000,
            "mortgage_type": "HELOC",
            "mortgage_amount": 125000,
            "mortgage_date": (datetime.utcnow() - timedelta(days=15)).isoformat(),
            "has_recent_permit": False,
        },
        {
            "address": "8901 Sand Point Way NE, Seattle, WA 98115",
            "city": "Seattle",
            "state": "WA",
            "zip": "98115",
            "sim_id": "SIM-HELOC-2",
            "property_value": 1200000,
            "mortgage_type": "HELOC",
            "mortgage_amount": 200000,
            "mortgage_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "has_recent_permit": False,
        },
    ],
    "sales": [
        {
            "address": "3456 Eastlake Ave E, Seattle, WA 98102",
            "city": "Seattle",
            "state": "WA",
            "zip": "98102",
            "sim_id": "SIM-SALE-1",
            "sale_amount": 1100000,
            "sale_date": (datetime.utcnow() - timedelta(days=20)).isoformat(),
            "mortgage_type": "HELOC",
            "mortgage_amount": 150000,
            "mortgage_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
            "has_recent_permit": False,
            "property_value": 1100000,
        },
        {
            "address": "5678 Wallingford Ave N, Seattle, WA 98103",
            "city": "Seattle",
            "state": "WA",
            "zip": "98103",
            "sim_id": "SIM-SALE-2",
            "sale_amount": 875000,
            "sale_date": (datetime.utcnow() - timedelta(days=40)).isoformat(),
            "mortgage_type": "HELOC",
            "mortgage_amount": 80000,
            "mortgage_date": (datetime.utcnow() - timedelta(days=25)).isoformat(),
            "has_recent_permit": False,
            "property_value": 875000,
        },
    ],
    "escrow": [
        {
            "address": "7890 15th Ave NE, Seattle, WA 98115",
            "city": "Seattle",
            "state": "WA",
            "zip": "98115",
            "zpid": "SIM-ESC-1",
            "previous_status": "Pending",
            "current_status": "For Sale",
            "price": 920000,
        },
    ],
}

SOURCE_MAP = {
    "permit_sniper": "sdci",
    "emergency_plumbing": "sdci",
    "heloc": "recorder",
    "sales": "recorder",
    "escrow": "zillow_status",
}


@router.post("/run")
async def run_simulation(req: SimulationRequest, background_tasks: BackgroundTasks):
    """Start a simulation run."""
    sim_id = str(uuid.uuid4())[:8]
    _simulations[sim_id] = {
        "status": "queued",
        "progress": 0,
        "created_leads": 0,
        "log": [f"[{_now()}] Simulation {sim_id} queued, delay={req.delay_seconds}s"],
    }
    background_tasks.add_task(_run_simulation, sim_id, req.delay_seconds, req.scenarios)
    return {"sim_id": sim_id, "status": "queued"}


@router.get("/status/{sim_id}")
async def get_sim_status(sim_id: str):
    """Check simulation status."""
    sim = _simulations.get(sim_id)
    if not sim:
        return {"error": "Simulation not found", "sim_id": sim_id}
    return SimulationStatus(
        sim_id=sim_id,
        status=sim["status"],
        progress=sim["progress"],
        created_leads=sim["created_leads"],
        log=sim["log"][-20:],
    )


async def _run_simulation(sim_id: str, delay: int, scenarios: List[str]):
    """Background simulation runner."""
    sim = _simulations[sim_id]
    sim["status"] = "waiting"
    sim["log"].append(f"[{_now()}] Waiting {delay}s before starting...")

    await asyncio.sleep(delay)

    sim["status"] = "running"
    sim["log"].append(f"[{_now()}] Simulation started")

    # Create fake parser jobs in DB
    _create_fake_jobs(sim)

    total_records = sum(len(TEMPLATE_RECORDS.get(s, [])) for s in scenarios)
    processed = 0
    created = 0

    for scenario in scenarios:
        records = TEMPLATE_RECORDS.get(scenario, [])
        source = SOURCE_MAP.get(scenario, "sdci")
        sim["log"].append(f"[{_now()}] Processing scenario: {scenario} ({len(records)} records, source={source})")

        for record in records:
            try:
                case_types = ingest_record_to_leads(record, source)
                if case_types:
                    created += len(case_types)
                    addr = record.get("address", "?")
                    for ct in case_types:
                        sim["log"].append(f"[{_now()}] LEAD CREATED: {addr} -> {ct}")
                else:
                    sim["log"].append(f"[{_now()}] No lead match for: {record.get('address', '?')}")
            except Exception as e:
                sim["log"].append(f"[{_now()}] ERROR processing record: {e}")
                logger.error(f"Simulation record error: {e}")

            processed += 1
            sim["progress"] = int(processed / max(total_records, 1) * 80)
            sim["created_leads"] = created
            await asyncio.sleep(0.5)

    # Mock outbound phase
    sim["log"].append(f"[{_now()}] Starting mock outbound phase...")
    sim["progress"] = 85
    _mock_outbound(sim)
    sim["progress"] = 95

    # Send Telegram summary
    await _send_telegram_summary(sim_id, sim, created, scenarios)

    # Complete fake jobs
    _complete_fake_jobs()

    sim["status"] = "completed"
    sim["progress"] = 100
    sim["log"].append(f"[{_now()}] Simulation completed: {created} leads created")


def _create_fake_jobs(sim):
    """Create fake parser job records so they appear in the Jobs list."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        for tbl, jtype in [("permit_jobs", "SDCI simulation"), ("mbp_jobs", "MBP simulation")]:
            try:
                cursor.execute(f"""
                    INSERT INTO {tbl} (status, started_at, year, limit_count)
                    VALUES ('running', '{now}', 2026, 0)
                """)
            except Exception as e:
                sim["log"].append(f"[{_now()}] Could not create fake {jtype} job: {e}")
        conn.commit()
        conn.close()
        sim["log"].append(f"[{_now()}] Fake parser jobs created (running)")
    except Exception as e:
        sim["log"].append(f"[{_now()}] DB error creating jobs: {e}")


def _complete_fake_jobs():
    """Mark fake running jobs as completed."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        for tbl in ["permit_jobs", "mbp_jobs"]:
            try:
                cursor.execute(f"UPDATE {tbl} SET status='completed', completed_at='{now}' WHERE status='running'")
            except Exception:
                pass
        conn.commit()
        conn.close()
    except Exception:
        pass


def _mock_outbound(sim):
    """Mock Lob/Apollo outbound by updating lead statuses via SQLAlchemy ORM."""
    try:
        try:
            from backend.database_setup import SessionLocal
            from backend.db_models import Lead
        except ImportError:
            from database_setup import SessionLocal
            from db_models import Lead

        db = SessionLocal()
        now = datetime.utcnow()

        # Mark some leads as letter_sent (Lob mock)
        lob_leads = db.query(Lead).filter(
            Lead.status == 'new', Lead.sent_lob_at.is_(None)
        ).limit(3).all()
        for lead in lob_leads:
            lead.status = 'letter_sent'
            lead.sent_lob_at = now

        # Mark some leads as email_sent (Apollo mock)
        apollo_leads = db.query(Lead).filter(
            Lead.status == 'new', Lead.sent_apollo_at.is_(None)
        ).limit(2).all()
        for lead in apollo_leads:
            lead.status = 'email_sent'
            lead.sent_apollo_at = now

        db.commit()
        db.close()
        sim["log"].append(f"[{_now()}] Mock outbound: {len(lob_leads)} Lob letters + {len(apollo_leads)} Apollo emails")
    except Exception as e:
        sim["log"].append(f"[{_now()}] Mock outbound error: {e}")


async def _send_telegram_summary(sim_id, sim, leads_created, scenarios):
    """Send Telegram notification with simulation results."""
    try:
        try:
            from backend.services.outbound.telegram_bot import send_alert
        except ImportError:
            from services.outbound.telegram_bot import send_alert

        message = (
            f"SIMULATION COMPLETE [{sim_id}]\n"
            f"Scenarios: {', '.join(scenarios)}\n"
            f"Leads created: {leads_created}\n"
            f"Status: completed"
        )
        await send_alert(message)
        sim["log"].append(f"[{_now()}] Telegram summary sent")
    except Exception as e:
        sim["log"].append(f"[{_now()}] Telegram send failed (non-critical): {e}")


def _now():
    return datetime.utcnow().strftime("%H:%M:%S")
