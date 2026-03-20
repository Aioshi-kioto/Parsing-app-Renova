"""
Zillow Status Tracker (Sprint 2).

Задача модуля:
  - Извлекать из БД Zillow (или `zillow_status_history`) объекты в статусе "Pending".
  - Опрашивать Zillow актуальный статус (реализуется через API/Scraper).
  - Если статус сменился с "Pending" на "For Sale" (Escrow Fallout),
    передавать агрегированный record в Rules Engine.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from backend.database_setup import SessionLocal
from backend.db_models import ZillowHome, ZillowStatusHistory
from backend.services.lead_pipeline import ingest_record_to_leads

logger = logging.getLogger(__name__)


def fetch_current_zillow_status(zpid: str) -> Dict:
    """
    TODO: Заменить на реальный парсер/API запрос.
    Сейчас заглушка, которая возвращает псевдо-данные для тестов.
    """
    # В реальности тут будет async Playwright запрос на zillow.com/homedetails/{zpid}_zpid/
    return {
        "zpid": zpid,
        "status": "For Sale",  # Симулируем Fallout
        "price": 850000.0,
        "zip": "98103",
        "address": f"Mock Address for {zpid}",
    }


def track_zillow_statuses() -> int:
    """
    Основной Job.
    1. Ищет все дома со статусом Pending.
    2. Запрашивает их актуальный статус.
    3. Сохраняет историю в `zillow_status_history`.
    4. Если поймал Escrow Fallout (Pending -> For Sale) -> шлёт в Rules Engine.
    
    Возвращает количество новых лидов.
    """
    db: Session = SessionLocal()
    leads_created = 0
    
    try:
        # Для простоты ищем дома, у которых есть сохраненный статус Pending
        # Либо в zillow_homes (если парсер сохраняет туда), либо в zillow_status_history
        # Возьмём уникальные zpid из zillow_status_history, где последний статус == Pending
        
        # Получаем список zpid, за которыми надо следить. 
        # Допустим, мы добавили их ранее при первичном парсинге Zillow.
        # Пока просто симулируем выборку:
        pending_homes = db.query(ZillowStatusHistory).filter(
            ZillowStatusHistory.status == "Pending"
        ).all()
        
        if not pending_homes:
            logger.info("Zillow Status Tracker: нет домов в статусе Pending для отслеживания.")
            # Симулятор для первой проверки (чтобы тесты и демо работали)
            mock_zpids = ["1234567"]
        else:
            # Дедубликация по zpid
            mock_zpids = list({h.zpid for h in pending_homes})
            
        for zpid in mock_zpids:
            try:
                # 1. Запрос актуального статуса
                new_data = fetch_current_zillow_status(zpid)
                new_status = new_data.get("status")
                
                # 2. Получаем предыдущий статус из базы (самый свежий)
                last_history = (
                    db.query(ZillowStatusHistory)
                    .filter(ZillowStatusHistory.zpid == zpid)
                    .order_by(ZillowStatusHistory.checked_at.desc())
                    .first()
                )
                
                old_status = last_history.status if last_history else "Pending" # Mock
                
                # 3. Сохраняем новый срез истории
                history = ZillowStatusHistory(
                    zpid=zpid,
                    address=new_data.get("address"),
                    zipcode=new_data.get("zip"),
                    price=new_data.get("price"),
                    status=new_status,
                    raw_data=new_data
                )
                db.add(history)
                db.commit()
                
                # 4. Проверяем на Escrow Fallout
                if str(old_status).upper() == "PENDING" and str(new_status).upper() in ("FOR SALE", "BACK ON MARKET"):
                    logger.info("Пойман Escrow Fallout для zpid %s", zpid)
                    
                    # Формируем record для Rules Engine (Кейс 6)
                    record = {
                        "address": new_data.get("address"),
                        "city": "Seattle",
                        "zip": new_data.get("zip"),
                        "price": new_data.get("price"),
                        "previous_status": old_status,
                        "current_status": new_status,
                        "zpid": zpid,
                        "days_in_pending": 14 # Условно, нужно вычислять
                    }
                    
                    touched_cases = ingest_record_to_leads(record, source="zillow_status")
                    if touched_cases:
                        leads_created += len(touched_cases)
                        
            except Exception as e:
                logger.error("Ошибка при проверке Zillow zpid %s: %s", zpid, e)
                db.rollback()
                
        return leads_created
        
    except Exception as e:
        logger.error("Zillow Tracker Error: %s", e)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Запуск Zillow Status Tracker...")
    created = track_zillow_statuses()
    logger.info("Обработка завершена. Затронуто кейсов: %s", created)
