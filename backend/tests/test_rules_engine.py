"""
Unit-тесты для Rules Engine.

Запуск: python -m pytest backend/tests/test_rules_engine.py -v
"""
import sys
import os

# Добавляем backend в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from services.rules_engine import (
    is_emergency_plumbing,
    is_permit_sniper,
    is_electrical_rewire,
    is_storm_roof_damage,
    is_heloc_no_permit,
    is_new_purchase_heloc,
    is_mechanics_lien,
    is_escrow_fallout,
    classify_lead,
    LeadMatch,
)


# ==============================
# is_emergency_plumbing
# ==============================

class TestEmergencyPlumbing:
    def test_positive_beacon_plumbing(self):
        record = {
            "permit_type": "Plumbing",
            "applicant_name": "BEACON PLUMBING & MECHANICAL",
            "applied_date": "2024-01-15",
            "issued_date": "2024-01-15",
        }
        assert is_emergency_plumbing(record) is True

    def test_positive_roto_rooter(self):
        record = {
            "permit_type": "Plumbing",
            "applicant_name": "ROTO-ROOTER SERVICES",
            "applied_date": "2024-03-10",
            "issued_date": "2024-03-10",
        }
        assert is_emergency_plumbing(record) is True

    def test_negative_regular_plumber(self):
        """Обычный сантехник, не аварийный."""
        record = {
            "permit_type": "Plumbing",
            "applicant_name": "Smith Plumbing LLC",
            "applied_date": "2024-01-15",
            "issued_date": "2024-01-15",
        }
        assert is_emergency_plumbing(record) is False

    def test_negative_different_date(self):
        """Beacon, но applied != issued — не экстренный."""
        record = {
            "permit_type": "Plumbing",
            "applicant_name": "BEACON PLUMBING",
            "applied_date": "2024-01-15",
            "issued_date": "2024-01-20",
        }
        assert is_emergency_plumbing(record) is False

    def test_negative_wrong_permit_type(self):
        """Электрический, а не сантехнический."""
        record = {
            "permit_type": "Electrical",
            "applicant_name": "BEACON PLUMBING",
            "applied_date": "2024-01-15",
            "issued_date": "2024-01-15",
        }
        assert is_emergency_plumbing(record) is False

    def test_contractor_name_fallback(self):
        """Если applicant_name пуст, проверяем contractor_name."""
        record = {
            "permit_type": "Plumbing",
            "applicant_name": "",
            "contractor_name": "FOX PLUMBING & HEATING",
            "applied_date": "2024-02-01",
            "issued_date": "2024-02-01",
        }
        assert is_emergency_plumbing(record) is True


# ==============================
# is_permit_sniper
# ==============================

class TestPermitSniper:
    def test_positive_architecture_firm(self):
        record = {
            "permit_type": "Structural",
            "applicant_name": "Olson Kundig Architecture",
            "contractor_name": "Turner Construction",
        }
        assert is_permit_sniper(record) is True

    def test_positive_design_studio(self):
        record = {
            "permit_type_mapped": "Major Alteration",
            "applicant_name": "Bohlin Cywinski Jackson Design Studio",
            "contractor_name": "ABC Builders",
        }
        assert is_permit_sniper(record) is True

    def test_negative_owner_builder(self):
        """Архитектурная фирма, но нет подрядчика (owner-builder)."""
        record = {
            "permit_type": "Structural",
            "applicant_name": "Modern Architecture Inc",
            "contractor_name": "",
        }
        assert is_permit_sniper(record) is False

    def test_negative_wrong_type(self):
        """Электрический пермит — не структурный."""
        record = {
            "permit_type": "Electrical",
            "applicant_name": "Design Associates",
            "contractor_name": "Some Builder",
        }
        assert is_permit_sniper(record) is False

    def test_negative_no_architecture(self):
        """Обычная компания, не архитектурная."""
        record = {
            "permit_type": "Foundation",
            "applicant_name": "Smith & Sons LLC",
            "contractor_name": "Turner Construction",
        }
        assert is_permit_sniper(record) is False


# ==============================
# is_electrical_rewire
# ==============================

class TestElectricalRewire:
    def test_positive_knob_and_tube(self):
        record = {
            "permit_type": "Electrical",
            "description": "Remove existing knob and tube wiring, rewire entire house",
        }
        assert is_electrical_rewire(record) is True

    def test_positive_whole_house_rewire(self):
        record = {
            "permit_type": "Electrical",
            "description": "Whole house rewire - 200 amp panel upgrade",
        }
        assert is_electrical_rewire(record) is True

    def test_negative_ev_charger(self):
        """EV charger — исключаем."""
        record = {
            "permit_type": "Electrical",
            "description": "Install Tesla EV charger in garage, panel upgrade",
        }
        assert is_electrical_rewire(record) is False

    def test_negative_solar(self):
        """Solar panel — исключаем."""
        record = {
            "permit_type": "Electrical",
            "description": "Solar panel installation, whole house rewire needed",
        }
        assert is_electrical_rewire(record) is False

    def test_negative_wrong_type(self):
        """Не электрический пермит."""
        record = {
            "permit_type": "Plumbing",
            "description": "Remove existing knob and tube wiring",
        }
        assert is_electrical_rewire(record) is False

    def test_negative_generic_electrical(self):
        """Обычный электрический пермит без K&T."""
        record = {
            "permit_type": "Electrical",
            "description": "Install new outlets in kitchen",
        }
        assert is_electrical_rewire(record) is False


# ==============================
# is_storm_roof_damage
# ==============================

class TestStormRoofDamage:
    def test_positive_tree_impact(self):
        record = {
            "permit_type": "Roofing",
            "description": "Emergency repair - tree impact damaged rafters and sheathing",
        }
        assert is_storm_roof_damage(record) is True

    def test_positive_stfi(self):
        record = {
            "permit_type": "STFI",
            "description": "Structural repair to truss system after storm damage",
        }
        assert is_storm_roof_damage(record) is True

    def test_negative_regular_roof(self):
        """Обычная замена крыши — без шторма."""
        record = {
            "permit_type": "Roofing",
            "description": "Reroof with architectural shingles",
        }
        assert is_storm_roof_damage(record) is False

    def test_negative_wrong_type(self):
        record = {
            "permit_type": "Plumbing",
            "description": "Storm damage repair",
        }
        assert is_storm_roof_damage(record) is False


# ==============================
# classify_lead
# ==============================

class TestClassifyLead:
    def test_sdci_emergency(self):
        record = {
            "permit_type": "Plumbing",
            "applicant_name": "BEACON PLUMBING",
            "applied_date": "2024-01-15",
            "issued_date": "2024-01-15",
        }
        matches = classify_lead(record, "sdci")
        assert len(matches) == 1
        assert matches[0].case_type == "EMERGENCY_PLUMBING"
        assert matches[0].priority == "RED"
        assert matches[0].autonomy_mode == "semi_autonomous"
        assert matches[0].initial_status == "pending_review"

    def test_sdci_permit_sniper(self):
        record = {
            "permit_type": "Structural",
            "applicant_name": "ABC Architecture",
            "contractor_name": "Turner Construction",
        }
        matches = classify_lead(record, "sdci")
        assert len(matches) == 1
        assert matches[0].case_type == "PERMIT_SNIPER"
        assert matches[0].initial_status == "new"

    def test_no_match(self):
        record = {
            "permit_type": "Mechanical",
            "applicant_name": "HVAC Corp",
            "description": "Install furnace",
        }
        matches = classify_lead(record, "sdci")
        assert len(matches) == 0

    def test_recorder_source_heloc(self):
        """Recorder источник: Fresh Cash → HELOC_NO_PERMIT."""
        record = {
            "doc_type_code": "DT",
            "amount": 75000,
            "has_recent_permit": False,
        }
        matches = classify_lead(record, "recorder")
        assert any(m.case_type == "HELOC_NO_PERMIT" for m in matches)

    def test_zillow_status_source(self):
        """Zillow status источник: Escrow Fallout."""
        record = {
            "previous_status": "Pending",
            "current_status": "For Sale",
            "price": 900000,
            "zip": "98103",
        }
        matches = classify_lead(record, "zillow_status")
        assert any(m.case_type == "ESCROW_FALLOUT" for m in matches)

    def test_mbp_source_works(self):
        """MyBuildingPermit тоже проходит через SDCI-детекторы."""
        record = {
            "permit_type": "Electrical",
            "description": "Knob and tube removal and whole house rewire",
        }
        matches = classify_lead(record, "mybuildingpermit")
        assert len(matches) == 1
        assert matches[0].case_type == "ELECTRICAL_REWIRE"


# ==============================
# Recorder detectors
# ==============================


class TestRecorderDetectors:
    def test_is_heloc_no_permit_positive(self):
        record = {
            "doc_type_code": "DT",
            "amount": 80000,
            "has_recent_permit": False,
        }
        assert is_heloc_no_permit(record) is True

    def test_is_heloc_no_permit_negative_amount(self):
        record = {"doc_type_code": "DT", "amount": 10000, "has_recent_permit": False}
        assert is_heloc_no_permit(record) is False

    def test_is_new_purchase_heloc_positive(self):
        record = {
            "has_recent_sale": True,
            "has_recent_heloc": True,
            "has_recent_permit": False,
        }
        assert is_new_purchase_heloc(record) is True

    def test_is_new_purchase_heloc_negative_flags(self):
        record = {
            "has_recent_sale": True,
            "has_recent_heloc": False,
            "has_recent_permit": False,
        }
        assert is_new_purchase_heloc(record) is False

    def test_is_mechanics_lien_positive(self):
        record = {
            "doc_type_text": "MECHANICS LIEN",
            "amount": 30000,
        }
        assert is_mechanics_lien(record) is True

    def test_is_mechanics_lien_negative_amount(self):
        record = {
            "doc_type_text": "MECHANICS LIEN",
            "amount": 5000,
        }
        assert is_mechanics_lien(record) is False


# ==============================
# Zillow status detector
# ==============================


class TestEscrowFalloutDetector:
    def test_positive_escrow_fallout(self):
        record = {
            "previous_status": "Pending",
            "current_status": "Back on Market",
            "price": 950000,
            "zip": "98117",
        }
        assert is_escrow_fallout(record) is True

    def test_negative_wrong_status(self):
        record = {
            "previous_status": "Active",
            "current_status": "For Sale",
            "price": 950000,
            "zip": "98117",
        }
        assert is_escrow_fallout(record) is False
