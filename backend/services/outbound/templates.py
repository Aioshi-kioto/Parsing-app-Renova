# -*- coding: utf-8 -*-
"""
Шаблоны outbound-каналов.

Источник истины: таблица outbound_templates.
Если записи ещё не сидированы, берём DEFAULT_TEMPLATES и создаём их в БД.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from backend.database_setup import SessionLocal
    from backend.db_models import OutboundTemplate
except Exception:
    from database_setup import SessionLocal
    from db_models import OutboundTemplate

# case_code -> (email_subject, email_body, sms_body)
DEFAULT_TEMPLATES = {
    "GENERAL": (
        "Ваш строительный проект на {street_name}",
        """Привет {owner_name},

Мы осуществляем мониторинг разрешений в Сиэтле и видим вашу свежую заявку. Renova Contractors специализируется на высококачественных ремонтах "под ключ". Если вы сейчас на стадии выбора генерального подрядчика или столкнулись с задержками — позвоните нам.

— Renova Contractors""",
        "Renova: видим ваш проект на {street_name}. Нужна помощь с ремонтом под ключ? Звоните.",
    ),
    "PERMIT_SNIPER": (
        "Ваш проект на {street_name} / Renova",
        """Привет {owner_name},

Я Миша, основатель Renova Contractors. Видел объём вашего нового проекта в Сиэтле — направление отличное. Мы выполняем сложные структурные ремоделинги для независимых дизайнеров. Хотел бы пригласить вас в наш шоурум в Баллард — посмотрите библиотеку финишей, выпьем кофе, и я узнаю, стоит ли нашим командам попасть в ваш список подрядчиков. Когда есть 15 минут?

— Миша, Renova Contractors""",
        "Renova: ваш проект на {street_name}. Приглашаем в шоурум в Баллард — обсудим подряд. Когда удобно?",
    ),
    "EMERGENCY_PLUMBING": (
        "Восстановление после затопления на {street_name}",
        """Привет {owner_name},

Мы видим, что на вашем объекте была аварийная ситуация с сантехникой. Beacon Plumbing перекрыли воду и заменили оборудование — но они не занимаются восстановлением. Вода уже проникла в стены и пол. Не ждите появления чёрной плесени. Renova приедет завтра с тепловизором, задокументирует скрытую влагу для страховой и возьмёт на себя полный снос и восстановление — покрывается страховой выплатой.

— Renova Contractors""",
        "Renova: затопление на {street_name}. Тепловизор + восстановление под страховку. Звоните — приедем завтра.",
    ),
    "ELECTRICAL_REWIRE": (
        "Электрика и ремонт на {street_name}",
        """Привет {owner_name},

Видим вашу заявку по электрике (K&T / rewire). Пока стены открыты — идеальное время для перепланировки ванной или кухни. Renova делает полный ремонт под ключ с учётом новых коммуникаций. Бесплатная оценка по объёму работ.

— Renova Contractors""",
        "Renova: электрика на {street_name}. Пока стены открыты — ремонт под ключ. Бесплатная оценка.",
    ),
    "STORM_ROOF_DAMAGE": (
        "Повреждение кровли на {street_name}",
        """Привет {owner_name},

Отслеживаем разрешения по кровле и видим ваш объект после шторма (дерево, стропила, обшивка). Renova специализируется на срочном ремонте кровли и структурном восстановлении. Можем приехать для осмотра и сметы.

— Renova Contractors""",
        "Renova: кровля после шторма на {street_name}. Осмотр и смета — звоните.",
    ),
    "HELOC_NO_PERMIT": (
        "Планируете ремонт на {street_name}?",
        """Привет {owner_name},

Я Миша, владелец Renova Contractors в Сиэтле. Если вы готовитесь к серьёзному ремонту в этом году, главная проблема — очередь в SDCI за пермитами. Мы предлагаем бесплатную консультацию по объёму работ, чтобы вы не попали в типичные ловушки с пермитами в King County. Напишите мне, если вы в стадии планирования.

— Миша, Renova Contractors""",
        "Renova: ремонт на {street_name}. Консультация по пермитам SDCI — бесплатно. Напишите или позвоните.",
    ),
    "NEW_PURCHASE_HELOC": (
        "Новый дом на {street_name} — ремонт под ключ",
        """Привет {owner_name},

Поздравляем с покупкой. Видим, что вы на {street_name} — год постройки подсказывает, что ремонт может понадобиться. Renova делает полный ремонт под ключ и помогает с пермитами в King County. Бесплатная консультация и смета.

— Renova Contractors""",
        "Renova: новый дом на {street_name}. Ремонт под ключ + пермиты. Бесплатная консультация.",
    ),
    "MECHANICS_LIEN": (
        "Завершение стройки на {street_name}",
        """Уважаемый(ая) {owner_name},

Мы отслеживаем публичные записи King County и заметили недавний арест имущества на вашей собственности. Renova выступает как «Rescue GC» для дорогих домов Сиэтла. Мы обеспечиваем прозрачное управление проектом для завершения заморозившихся строек без споров. Когда будете готовы двигаться дальше — поговорим.

— Renova Contractors""",
        "Renova: завершение замороженной стройки на {street_name}. Rescue GC — звоните.",
    ),
    "ESCROW_FALLOUT": (
        "Ваш листинг на {address} — решение для эскроу",
        """Привет {owner_name},

Вижу ваш листинг на {street_name} вернулся с Pending. Думаю, инспектор нашёл воду в подвале или проблему с плесенью? Не снижайте цену на $100k. Renova может приехать завтра, всё высушить, вырезать гниль, сделать структурное восстановление и дать сертификат. Продавец платит нам из эскроу после успешного закрытия следующей сделки.

— Renova Contractors""",
        "Renova: листинг {street_name} с Pending. Вода/плесень — мы решаем под эскроу. Звоните.",
    ),
}


def _default_template_payload(case_type: str) -> dict[str, Any]:
    subj, email_body, sms_body = DEFAULT_TEMPLATES[case_type]
    return {
        "case_type": case_type,
        "email_subject": subj,
        "email_body": email_body,
        "sms_body": sms_body,
        "lob_template_id": None,
        "lob_body_html": None,
    }


def seed_default_templates() -> None:
    db = SessionLocal()
    try:
        existing = {row.case_type for row in db.query(OutboundTemplate.case_type).all()}
        for case_type in DEFAULT_TEMPLATES:
            if case_type in existing:
                continue
            payload = _default_template_payload(case_type)
            db.add(
                OutboundTemplate(
                    case_type=payload["case_type"],
                    email_subject=payload["email_subject"],
                    email_body=payload["email_body"],
                    sms_body=payload["sms_body"],
                    lob_template_id=payload["lob_template_id"],
                    lob_body_html=payload["lob_body_html"],
                    updated_at=datetime.now(timezone.utc),
                )
            )
        db.commit()
    finally:
        db.close()


def _row_to_payload(row: OutboundTemplate) -> dict[str, Any]:
    return {
        "case_type": row.case_type,
        "email_subject": row.email_subject,
        "email_body": row.email_body,
        "sms_body": row.sms_body,
        "lob_template_id": row.lob_template_id,
        "lob_body_html": row.lob_body_html,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_all_templates() -> list[dict[str, Any]]:
    seed_default_templates()
    db = SessionLocal()
    try:
        rows = db.query(OutboundTemplate).order_by(OutboundTemplate.case_type.asc()).all()
        return [_row_to_payload(r) for r in rows]
    finally:
        db.close()


def get_template_payload(case_code: str | None) -> dict[str, Any]:
    seed_default_templates()
    normalized = case_code if case_code in DEFAULT_TEMPLATES else "GENERAL"
    db = SessionLocal()
    try:
        row = db.query(OutboundTemplate).filter(OutboundTemplate.case_type == normalized).first()
        if row:
            return _row_to_payload(row)
        return _default_template_payload("GENERAL")
    finally:
        db.close()


def upsert_template(case_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    seed_default_templates()
    db = SessionLocal()
    try:
        row = db.query(OutboundTemplate).filter(OutboundTemplate.case_type == case_code).first()
        if row is None:
            row = OutboundTemplate(case_type=case_code)
            db.add(row)
        row.email_subject = payload.get("email_subject") or ""
        row.email_body = payload.get("email_body") or ""
        row.sms_body = payload.get("sms_body") or ""
        row.lob_template_id = payload.get("lob_template_id")
        row.lob_body_html = payload.get("lob_body_html")
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return _row_to_payload(row)
    finally:
        db.close()


def get_template(case_code: str | None) -> tuple[str, str, str]:
    """Совместимость со старым интерфейсом: (subject, email_body, sms_body)."""
    tpl = get_template_payload(case_code)
    return (
        tpl.get("email_subject") or "",
        tpl.get("email_body") or "",
        tpl.get("sms_body") or "",
    )


def render(
    template_tuple: tuple[str, str, str],
    owner_name: str = "",
    street_name: str = "",
    address: str = "",
) -> tuple[str, str, str]:
    """Подставляет значения в (subject, email_body, sms_body)."""
    subj, email, sms = template_tuple
    ctx = {
        "owner_name": owner_name or "there",
        "street_name": street_name or "your property",
        "address": address or street_name or "your property",
    }
    return (
        subj.format(**ctx),
        email.format(**ctx),
        sms.format(**ctx),
    )
