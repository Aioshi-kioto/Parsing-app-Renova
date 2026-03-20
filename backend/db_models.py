from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

# ===============================
# SPRINT 1: LEADS & OUTBOUND
# ===============================

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String, nullable=False, index=True)
    city = Column(String)
    zip = Column(String)
    case_type = Column(String, nullable=False)
    priority = Column(String, nullable=False) # RED, YELLOW, GREEN
    source = Column(String, nullable=False)   # sdci, zillow, recorder
    
    contact_name = Column(String)
    contact_email = Column(String)  # Основной email (deprecated for batchdata results)
    contact_phone = Column(String)  # Основной телефон (deprecated for batchdata results)
    
    # Дополнительные поля для BatchData
    owner_first_name = Column(String)
    owner_last_name = Column(String)
    owner_mailing_address = Column(String)
    owner_mailing_city = Column(String)
    owner_mailing_state = Column(String)
    owner_mailing_zip = Column(String)
    state = Column(String)
    is_entity = Column(Boolean, default=False)
    entity_name = Column(String)
    is_bankrupt = Column(Boolean, default=False)
    is_deceased = Column(Boolean, default=False)
    is_litigator = Column(Boolean, default=False) # TCPA Risk
    
    # Статусы: new -> pending_review -> approved -> letter_sent -> contacted -> closed
    status = Column(String, default="new", index=True) 
    
    # Audit Trail для Semi-Autonomous кейсов
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String) # email или имя админа
    approved_at = Column(DateTime(timezone=True))
    approval_reason = Column(String)
    raw_data = Column(JSON)
    matched_cases = Column(JSON)
    
    found_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    skip_traced_at = Column(DateTime(timezone=True), index=True) # Дата обогащения через BatchData
    sent_lob_at = Column(DateTime(timezone=True), index=True)
    sent_sendgrid_at = Column(DateTime(timezone=True), index=True) # Заменили Apollo
    call_due_at = Column(DateTime(timezone=True), index=True)
    notes = Column(String)
    
    outbound_logs = relationship("OutboundLog", back_populates="lead")
    phones = relationship("LeadPhone", back_populates="lead", cascade="all, delete-orphan")
    emails = relationship("LeadEmail", back_populates="lead", cascade="all, delete-orphan")


class BillingLog(Base):
    """
    Service usage and cost logging for analytics.
    """
    __tablename__ = "billing_logs"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=True)
    service_name = Column(String, index=True)  # 'batchdata', 'sendgrid', 'lob', 'twilio'
    event_type = Column(String)  # 'skip_trace', 'email_delivered', 'letter_created'
    cost_usd = Column(Float, default=0.0)

    # Relationship
    lead = relationship("Lead", backref="billing_logs")


class LeadPhone(Base):
    __tablename__ = "lead_phones"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), index=True)
    phone_number = Column(String, nullable=False)
    phone_type = Column(String) # mobile, landline
    score = Column(Integer)     # 0-100
    is_reachable = Column(Boolean)
    is_dnc = Column(Boolean)
    carrier = Column(String)
    
    lead = relationship("Lead", back_populates="phones")


class LeadEmail(Base):
    __tablename__ = "lead_emails"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), index=True)
    email_address = Column(String, nullable=False)
    is_deliverable = Column(Boolean)
    
    lead = relationship("Lead", back_populates="emails")


class OutboundLog(Base):
    __tablename__ = "outbound_log"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id"))
    channel = Column(String) # lob, sendgrid, telegram
    status = Column(String)  # sent, failed
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    external_id = Column(String)  # ltr_... (Lob) or X-Message-Id (SendGrid)
    response = Column(JSON)
    
    lead = relationship("Lead", back_populates="outbound_logs")


class OutboundTemplate(Base):
    __tablename__ = "outbound_templates"

    case_type = Column(String, primary_key=True, index=True)  # PERMIT_SNIPER, GENERAL, etc.
    email_subject = Column(String, nullable=False)
    email_body = Column(String, nullable=False)
    lob_template_id = Column(String)  # tmpl_...
    lob_body_html = Column(String)
    sms_body = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ParserSetting(Base):
    __tablename__ = "parser_settings"

    parser_type = Column(String, primary_key=True)  # permit | mybuilding
    config_json = Column(JSON)
    channels_json = Column(JSON)
    fixed_settings_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledOperation(Base):
    __tablename__ = "scheduled_operations"

    id = Column(Integer, primary_key=True, index=True)
    operation_type = Column(String, nullable=False, index=True)  # permit | mybuilding
    status = Column(String, nullable=False, default="scheduled", index=True)  # scheduled|dispatching|dispatched|failed|cancelled|dead
    run_at_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    timezone = Column(String, nullable=False, default="UTC")
    payload_json = Column(JSON)
    channels_json = Column(JSON)
    fixed_settings_json = Column(JSON)
    created_by = Column(String)
    updated_by = Column(String)
    cancelled_by = Column(String)
    cancel_reason = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    dispatched_job_id = Column(Integer, index=True)
    dispatched_table = Column(String)
    dispatch_error = Column(String)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True))
    next_retry_at = Column(DateTime(timezone=True), index=True)
    dedupe_key = Column(String, unique=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    is_recurring = Column(Boolean, nullable=False, default=False)
    recurrence_interval_days = Column(Integer)
    next_run_at_utc = Column(DateTime(timezone=True), index=True)


# ===============================
# COST / BILLING
# ===============================

class ProviderCostPolicy(Base):
    __tablename__ = "provider_cost_policies"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)  # lob|sendgrid|batchdata|decodo|sms_beta
    pricing_mode = Column(String, nullable=False, default="per_event")  # per_event|per_gb|flat
    unit_cost_usd = Column(Float, nullable=False, default=0.0)
    unit_name = Column(String, nullable=False, default="event")  # event|letter|email|match|gb|mb
    is_active = Column(Boolean, nullable=False, default=True)
    effective_from = Column(DateTime(timezone=True), default=datetime.utcnow)
    effective_to = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ProviderBudget(Base):
    __tablename__ = "provider_budgets"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, unique=True, index=True)
    period = Column(String, nullable=False, default="monthly")
    budget_usd = Column(Float, nullable=False, default=0.0)
    warning_pct = Column(Integer, nullable=False, default=80)
    hard_limit_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ===============================
# ZILLOW TABLES
# ===============================

class ZillowJob(Base):
    __tablename__ = "zillow_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    urls = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)
    current_url_index = Column(Integer, default=0)
    total_urls = Column(Integer, nullable=False)
    homes_found = Column(Integer, default=0)
    unique_homes = Column(Integer, default=0)
    error_message = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    homes = relationship("ZillowHome", back_populates="job")


class ZillowHome(Base):
    __tablename__ = "zillow_homes"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("zillow_jobs.id"), index=True)
    zpid = Column(String, unique=True, index=True, nullable=False)
    address = Column(String)
    city = Column(String, index=True)
    state = Column(String)
    zipcode = Column(String)
    price = Column(Float, index=True)
    price_formatted = Column(String)
    beds = Column(Integer)
    baths = Column(Float)
    area_sqft = Column(Integer)
    lot_size = Column(Float)
    year_built = Column(Integer)
    home_type = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    date_sold = Column(String)
    sold_date_text = Column(String)
    zestimate = Column(Float)
    tax_assessed_value = Column(Float)
    has_image = Column(Boolean)
    detail_url = Column(String)
    raw_data = Column(JSON) # JSON fallback if not postgres
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("ZillowJob", back_populates="homes")

class ZillowStatusHistory(Base):
    __tablename__ = "zillow_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    zpid = Column(String, index=True, nullable=False)
    address = Column(String)
    zipcode = Column(String)
    price = Column(Float)
    status = Column(String, index=True) # For Sale, Pending, Sold
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    raw_data = Column(JSON)


# ===============================
# PERMIT TABLES
# ===============================

class PermitJob(Base):
    __tablename__ = "permit_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    year = Column(Integer, nullable=False)
    permit_class_filter = Column(String)
    permit_type_filter = Column(String)
    min_cost = Column(Float, default=5000)
    permits_found = Column(Integer, default=0)
    permits_verified = Column(Integer, default=0)
    owner_builders_found = Column(Integer, default=0)
    error_message = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    permits = relationship("Permit", back_populates="job")


class Permit(Base):
    __tablename__ = "permits"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("permit_jobs.id"), index=True)
    permit_num = Column(String, unique=True, index=True, nullable=False)
    permit_class = Column(String)
    permit_class_mapped = Column(String)
    permit_type_mapped = Column(String)
    permit_type_desc = Column(String)
    description = Column(String)
    est_project_cost = Column(Float)
    applied_date = Column(DateTime, index=True)
    issued_date = Column(DateTime)
    status_current = Column(String)
    address = Column(String)
    city = Column(String, index=True)
    state = Column(String)
    zipcode = Column(String)
    contractor_name = Column(String)
    is_owner_builder = Column(Boolean, index=True)
    verification_status = Column(String, default="pending")
    work_performer_text = Column(String)
    contacts_text = Column(String)
    portal_link = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job = relationship("PermitJob", back_populates="permits")


# ===============================
# MBP TABLES
# ===============================

class MBPJob(Base):
    __tablename__ = "mbp_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    jurisdictions = Column(String)
    days_back = Column(Integer, default=7)
    date_from_str = Column(String)
    date_to_str = Column(String)
    total_permits = Column(Integer, default=0)
    analyzed_count = Column(Integer, default=0)
    owner_builders_found = Column(Integer, default=0)
    elapsed_seconds = Column(Float)
    current_jurisdiction = Column(String)
    error_message = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    permits = relationship("MBPPermit", back_populates="job")


class MBPPermit(Base):
    __tablename__ = "mbp_permits"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("mbp_jobs.id"), index=True)
    permit_number = Column(String, nullable=False, index=True)
    jurisdiction = Column(String, index=True)
    project_name = Column(String)
    description = Column(String)
    permit_type = Column(String)
    permit_status = Column(String)
    address = Column(String)
    parcel = Column(String)
    applied_date = Column(String)
    issued_date = Column(String)
    applicant_name = Column(String)
    contractor_name = Column(String)
    contractor_license = Column(String)
    is_owner_builder = Column(Boolean, default=False, index=True)
    matches_target_type = Column(Boolean, default=False)
    permit_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("MBPJob", back_populates="permits")


# RECORDER TABLES (REMOVED - FROZEN)
