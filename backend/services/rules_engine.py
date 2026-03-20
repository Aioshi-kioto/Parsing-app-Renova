"""
Rules Engine — Классификация пермитов по 11 кейсам лидогенерации.

Каждый детектор получает dict с полями пермита и возвращает bool.
classify_lead() прогоняет запись через все детекторы и возвращает список совпадений.

Уровни автономности (из 03-LEAD-CASES.md):
  🟢 Fully Autonomous — отправка без участия человека
  🔴 Semi-Autonomous  — требует ручного Approve
  ⚪ Manual           — ручная загрузка данных
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


# ==============================
# Константы
# ==============================

EMERGENCY_PLUMBERS = [
    "BEACON PLUMBING", "ROTO-ROOTER", "FOX PLUMBING",
    "SOUTH WEST PLUMBING", "24/7", "EMERGENCY", "RESCUE",
    "BEST PLUMBING", "RAPID ROOTER",
]

ARCHITECTURE_KEYWORDS = [
    "ARCHITECTURE", "ARCHITECT", "DESIGN", "AIA", "STUDIO", "ASSOCIATES",
    "PLANNING", "ATELIER",
]

STRUCTURAL_PERMIT_TYPES = [
    "STRUCTURAL", "FRAMING", "FOUNDATION", "MAJOR ALTERATION",
]

KT_REWIRE_KEYWORDS = [
    "KNOB AND TUBE", "K&T", "WHOLE HOUSE REWIRE", "FIRE DAMAGE",
    "PANEL UPGRADE", "200 AMP",
]

KT_EXCLUDE_KEYWORDS = [
    "EV CHARGER", "TESLA", "SOLAR", "HEAT PUMP", "MINI SPLIT",
]

STORM_ROOF_KEYWORDS = [
    "TREE IMPACT", "STRUCTURAL REPAIR", "RAFTER", "TRUSS",
    "SHEATHING", "TARPING", "STORM DAMAGE", "WIND DAMAGE",
    "FALLEN TREE",
]


# Recorder helpers
RECORDER_HELOC_TYPES = {"DT", "DEED OF TRUST"}
RECORDER_SALE_TYPES = {"WD", "WARRANTY DEED"}


# ==============================
# Data classes
# ==============================

@dataclass
class LeadMatch:
    """Результат классификации одного пермита."""
    case_type: str
    priority: str          # RED, YELLOW, GREEN
    autonomy_mode: str     # fully_autonomous, semi_autonomous, manual
    initial_status: str    # new или pending_review


# ==============================
# Вспомогательные функции
# ==============================

def _contains_any(text: Optional[str], keywords: List[str]) -> bool:
    """Проверяет, содержит ли текст хотя бы одно из ключевых слов (case-insensitive)."""
    if not text:
        return False
    text_upper = text.upper()
    return any(kw in text_upper for kw in keywords)


def _not_contains_any(text: Optional[str], keywords: List[str]) -> bool:
    """Проверяет, что текст НЕ содержит ни одного из ключевых слов."""
    if not text:
        return True
    text_upper = text.upper()
    return not any(kw in text_upper for kw in keywords)


def _normalize_permit_type(permit_type: Optional[str]) -> str:
    """Нормализует тип пермита для сравнения."""
    if not permit_type:
        return ""
    return permit_type.strip().upper()


def _same_day(date1: Optional[str], date2: Optional[str]) -> bool:
    """Проверяет, что две даты — один и тот же день."""
    if not date1 or not date2:
        return False
    try:
        # Поддержка нескольких форматов дат
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                d1 = datetime.strptime(str(date1)[:19], fmt).date()
                break
            except ValueError:
                continue
        else:
            return False

        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                d2 = datetime.strptime(str(date2)[:19], fmt).date()
                break
            except ValueError:
                continue
        else:
            return False

        return d1 == d2
    except Exception:
        return False


# ==============================
# Детекторы (Sprint 1: 4 из 11)
# ==============================

def is_emergency_plumbing(record: dict) -> bool:
    """
    Кейс 2: Predator Plumber — «Экстренный аварийный потоп»
    
    Триггер:
      - permit_type = Plumbing
      - applicant_name содержит аварийных сантехников
      - applied_date == issued_date (авто-апрув = экстренность)
    """
    ptype = _normalize_permit_type(record.get("permit_type") or record.get("permit_type_mapped"))
    if "PLUMBING" not in ptype:
        return False

    applicant = record.get("applicant_name") or record.get("contractor_name") or ""
    if not _contains_any(applicant, EMERGENCY_PLUMBERS):
        return False

    # Авто-апрув = applied_date == issued_date (экстренность)
    applied = record.get("applied_date")
    issued = record.get("issued_date")
    if applied and issued and not _same_day(str(applied), str(issued)):
        return False

    return True


def is_permit_sniper(record: dict) -> bool:
    """
    Кейс 1: Permit Sniper — «Архитектурные проекты»
    
    Триггер:
      - permit_type ∈ [Structural, Framing, Foundation, Major Alteration]
      - applicant_name содержит Architecture / Design / AIA / Studio
      - contractor_name IS NOT NULL (профессиональный проект, не owner-builder)
    """
    ptype = _normalize_permit_type(record.get("permit_type") or record.get("permit_type_mapped"))
    if not any(st in ptype for st in STRUCTURAL_PERMIT_TYPES):
        return False

    applicant = record.get("applicant_name") or ""
    if not _contains_any(applicant, ARCHITECTURE_KEYWORDS):
        return False

    contractor = record.get("contractor_name")
    if not contractor or not contractor.strip():
        return False

    return True


def is_electrical_rewire(record: dict) -> bool:
    """
    Кейс 7: Swiss Cheese — «Электрический Swiss Cheese»
    
    Триггер:
      - permit_type = Electrical
      - description содержит K&T / whole house rewire / fire damage
      - description НЕ содержит EV charger / Tesla / Solar
    """
    ptype = _normalize_permit_type(record.get("permit_type") or record.get("permit_type_mapped"))
    if "ELECTRICAL" not in ptype:
        return False

    desc = record.get("description") or record.get("permit_type_desc") or ""
    if not _contains_any(desc, KT_REWIRE_KEYWORDS):
        return False

    if not _not_contains_any(desc, KT_EXCLUDE_KEYWORDS):
        return False

    return True


def is_storm_roof_damage(record: dict) -> bool:
    """
    Кейс 8: Broken Truss — «Повреждение кровли от шторма»
    
    Триггер:
      - permit_type ∈ [Roofing, STFI]
      - description содержит tree impact / truss / storm damage
    """
    ptype = _normalize_permit_type(record.get("permit_type") or record.get("permit_type_mapped"))
    if not ("ROOFING" in ptype or "STFI" in ptype or "ROOF" in ptype):
        return False

    desc = record.get("description") or record.get("permit_type_desc") or ""
    if not _contains_any(desc, STORM_ROOF_KEYWORDS):
        return False

    return True


# ==============================
# Sprint 2: Recorder & Zillow Status детекторы
# ==============================


def _get_upper(record: dict, key: str) -> str:
    val = record.get(key)
    return str(val).upper() if val is not None else ""


def _get_float(record: dict, key: str) -> float:
    val = record.get(key)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def is_heloc_no_permit(record: dict) -> bool:
    """
    Кейс 3: Fresh Cash — «Есть кредит, нет ремонта».

    Предполагаем, что record получен из агрегированных документов Recorder
    и описывает один объект недвижимости.

    Упрощённый триггер Sprint 2:
      - тип документа HELOC (Deed of Trust)
      - сумма кредита > 50k
      - нет флага recent_permit (has_recent_permit=False или отсутствует)
    """
    doc_type = _get_upper(record, "doc_type_code") or _get_upper(record, "doc_type_text")
    if not any(t in doc_type for t in RECORDER_HELOC_TYPES):
        return False

    amount = _get_float(record, "amount")
    if amount <= 50000:
        return False

    has_recent_permit = bool(record.get("has_recent_permit"))
    if has_recent_permit:
        return False

    return True


def is_new_purchase_heloc(record: dict) -> bool:
    """
    Кейс 4: New Money — «Купили + взяли кредит + не ремонтируют».

    Для Sprint 2 детектор опирается на агрегированный вид по адресу:
      - есть недавняя покупка (has_recent_sale=True)
      - есть недавний HELOC (has_recent_heloc=True)
      - нет свежих пермитов (has_recent_permit=False)

    Логику по датам/годам постройки можно донастроить в следующих спринтах.
    """
    if not record.get("has_recent_sale"):
        return False
    if not record.get("has_recent_heloc"):
        return False
    if record.get("has_recent_permit"):
        return False
    return True


def is_mechanics_lien(record: dict) -> bool:
    """
    Кейс 5: Mechanic's Lien — «Стройка заморожена судом».

    Упрощённый триггер Sprint 2:
      - тип документа содержит LIEN (doc_type_text или code)
      - сумма удержания > 20k
    """
    doc_type = _get_upper(record, "doc_type_text") or _get_upper(record, "doc_type_code")
    if "LIEN" not in doc_type:
        return False

    amount = _get_float(record, "amount")
    if amount <= 20000:
        return False

    return True


def is_escrow_fallout(record: dict) -> bool:
    """
    Кейс 6: Escrow Fallout — «Сделка сорвалась при инспекции».

    Ожидаемые поля record (агрегированный статус Zillow):
      - previous_status: строка, например \"Pending\"
      - current_status: строка, например \"For Sale\" / \"Back on Market\"
      - days_in_pending: int (10–14 по спецификации; в коде не жёстко)
      - price: float
      - zip: строка ZIP кода
    """
    prev_status = _get_upper(record, "previous_status")
    curr_status = _get_upper(record, "current_status")

    if prev_status != "PENDING":
        return False
    if curr_status not in ("FOR SALE", "BACK ON MARKET"):
        return False

    price = _get_float(record, "price")
    if price <= 800000:
        return False

    zip_code = _get_upper(record, "zip")
    if zip_code not in {"98103", "98117", "98115", "98112"}:
        return False

    return True


# ==============================
# Матрица автономности (Source of Truth)
# ==============================

AUTONOMY_MAP = {
    "PERMIT_SNIPER":       ("YELLOW", "fully_autonomous",  "new"),
    "EMERGENCY_PLUMBING":  ("RED",    "semi_autonomous",   "pending_review"),
    "HELOC_NO_PERMIT":     ("YELLOW", "fully_autonomous",  "new"),
    "NEW_PURCHASE_HELOC":  ("YELLOW", "fully_autonomous",  "new"),
    "MECHANICS_LIEN":      ("RED",    "semi_autonomous",   "pending_review"),
    "ESCROW_FALLOUT":      ("RED",    "fully_autonomous",  "new"),
    "ELECTRICAL_REWIRE":   ("GREEN",  "fully_autonomous",  "new"),
    "STORM_ROOF_DAMAGE":   ("GREEN",  "fully_autonomous",  "new"),
    "PROBATE_ESTATE":      ("YELLOW", "manual",            "new"),
    "B2B_PUBLIC_ADJUSTER": ("YELLOW", "fully_autonomous",  "new"),
    "B2B_HYGIENIST":       ("YELLOW", "fully_autonomous",  "new"),
    "GENERAL":             ("GREEN",  "manual",            "new"),
}


# ==============================
# Главная функция классификации
# ==============================

def classify_lead(record: dict, source: str) -> List[LeadMatch]:
    """
    Прогоняет запись через все детекторы и возвращает список совпадений.
    
    Args:
        record: dict с полями пермита (address, permit_type, applicant_name и т.д.)
        source: источник данных — "sdci", "mybuildingpermit", "recorder", "zillow_status"
    
    Returns:
        List[LeadMatch] — список найденных кейсов (может быть пустым или >1)
    """
    matches: List[LeadMatch] = []

    if source in ("sdci", "mybuildingpermit"):
        if is_emergency_plumbing(record):
            p, a, s = AUTONOMY_MAP["EMERGENCY_PLUMBING"]
            matches.append(LeadMatch("EMERGENCY_PLUMBING", p, a, s))

        if is_permit_sniper(record):
            p, a, s = AUTONOMY_MAP["PERMIT_SNIPER"]
            matches.append(LeadMatch("PERMIT_SNIPER", p, a, s))

        if is_electrical_rewire(record):
            p, a, s = AUTONOMY_MAP["ELECTRICAL_REWIRE"]
            matches.append(LeadMatch("ELECTRICAL_REWIRE", p, a, s))

        if is_storm_roof_damage(record):
            p, a, s = AUTONOMY_MAP["STORM_ROOF_DAMAGE"]
            matches.append(LeadMatch("STORM_ROOF_DAMAGE", p, a, s))
            
    # Если пермит не подошел ни под один уникальный кейс (и он не из дополнительных источников),
    # всё равно проверяем matches. Если пусто - ставим GENERAL.
    if not matches and source in ("sdci", "mybuildingpermit", "recorder", "zillow_status"):
        p, a, s = AUTONOMY_MAP["GENERAL"]
        matches.append(LeadMatch("GENERAL", p, a, s))

    # Sprint 2: recorder кейсы (3, 4, 5)
    if source == "recorder":
        if is_heloc_no_permit(record):
            p, a, s = AUTONOMY_MAP["HELOC_NO_PERMIT"]
            matches.append(LeadMatch("HELOC_NO_PERMIT", p, a, s))

        if is_new_purchase_heloc(record):
            p, a, s = AUTONOMY_MAP["NEW_PURCHASE_HELOC"]
            matches.append(LeadMatch("NEW_PURCHASE_HELOC", p, a, s))

        if is_mechanics_lien(record):
            p, a, s = AUTONOMY_MAP["MECHANICS_LIEN"]
            matches.append(LeadMatch("MECHANICS_LIEN", p, a, s))

    # Sprint 2: zillow_status кейс 6
    if source == "zillow_status":
        if is_escrow_fallout(record):
            p, a, s = AUTONOMY_MAP["ESCROW_FALLOUT"]
            matches.append(LeadMatch("ESCROW_FALLOUT", p, a, s))

    return matches
