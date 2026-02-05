"""
Permit Parser Service
Интеграция с Seattle Building Permits парсером
"""
import sys
from pathlib import Path
import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import (
    get_connection, update_permit_job, insert_permit, 
    update_permit_verification
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Конфигурация Socrata API
SOCRATA_CONFIG = {
    "domain": "data.seattle.gov",
    "dataset_id": "76t5-zqzr",
    "app_token": None,  # Опционально
}

# Accela Portal
ACCELA_BASE_URL = "https://cosaccela.seattle.gov"
ACCELA_PERMIT_URL = f"{ACCELA_BASE_URL}/portal/cap/capDetail.aspx"


def _get_date_range(year: int, month: Optional[int] = None, period: Optional[str] = None) -> tuple:
    """Возвращает (date_from, date_to) для запроса. period: 'last_month' | 'last_3_months' | 'year'"""
    from datetime import date
    
    today = date.today()
    
    if period in (None, "year", ""):
        return f"{year}-01-01", f"{year + 1}-01-01"
    
    if period == "last_month":
        # Предыдущий месяц
        if today.month == 1:
            start = date(today.year - 1, 12, 1)
            end = date(today.year, 1, 1)
        else:
            start = date(today.year, today.month - 1, 1)
            end = date(today.year, today.month, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    elif period == "last_3_months":
        # Последние 3 полных месяца (не включая текущий)
        if today.month <= 3:
            start = date(today.year - 1, today.month + 9, 1)  # e.g. Feb -> Nov prev year
        else:
            start = date(today.year, today.month - 3, 1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1)
        else:
            end = date(today.year, today.month + 1, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    elif month is not None and 1 <= month <= 12:
        date_from = f"{year}-{month:02d}-01"
        if month == 12:
            date_to = f"{year + 1}-01-01"
        else:
            date_to = f"{year}-{month + 1:02d}-01"
        return date_from, date_to
    else:
        return f"{year}-01-01", f"{year + 1}-01-01"


def build_soql_query(
    year: int = 2026,
    month: Optional[int] = None,
    period: Optional[str] = None,
    permit_class: Optional[str] = None,
    permit_type: str = "Building",
    contractor_is_null: bool = True,
    min_cost: float = 5000,
    limit: int = 10000,
    offset: int = 0,
) -> Dict[str, str]:
    """Построение SoQL запроса для фильтрации пермитов"""
    conditions = []
    
    date_from, date_to = _get_date_range(year, month, period)
    conditions.append(f"applieddate >= '{date_from}'")
    conditions.append(f"applieddate < '{date_to}'")
    
    # Фильтр по классу пермита
    if permit_class:
        # API Seattle ожидает "Single Family/Duplex" (без пробелов вокруг /)
        permit_class_normalized = permit_class.replace(" / ", "/").strip()
        conditions.append(f"permitclass = '{permit_class_normalized}'")
    
    # Фильтр по типу пермита
    if permit_type:
        conditions.append(f"permittypemapped = '{permit_type}'")
    
    # Фильтр: контрактор не указан
    if contractor_is_null:
        conditions.append("contractorcompanyname IS NULL")
    
    # Фильтр по минимальной стоимости
    if min_cost:
        conditions.append(f"estprojectcost >= {min_cost}")
    
    where_clause = " AND ".join(conditions)
    
    params = {
        "$where": where_clause,
        "$limit": str(limit),
        "$offset": str(offset),
        "$order": "applieddate DESC",
    }
    
    if SOCRATA_CONFIG.get("app_token"):
        params["$$app_token"] = SOCRATA_CONFIG["app_token"]
    
    return params


def fetch_permits_from_api(
    year: int = 2026,
    month: Optional[int] = None,
    period: Optional[str] = None,
    permit_class: Optional[str] = None,
    min_cost: float = 5000,
    limit: int = 10000,
) -> List[Dict[str, Any]]:
    """Получение пермитов из Seattle Open Data API"""
    base_url = f"https://{SOCRATA_CONFIG['domain']}/resource/{SOCRATA_CONFIG['dataset_id']}.json"
    
    params = build_soql_query(
        year=year,
        month=month,
        period=period,
        permit_class=permit_class,
        min_cost=min_cost,
        limit=limit,
    )
    
    logger.info(f"Fetching permits from {base_url}")
    logger.info(f"Query: {params['$where']}")
    
    with httpx.Client(timeout=60.0) as client:
        response = client.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
    
    logger.info(f"Fetched {len(data)} permits")
    return data


def extract_permit_data(raw_permit: Dict[str, Any]) -> Dict[str, Any]:
    """Извлечение структурированных данных из raw API response"""
    # Формируем ссылку на портал
    permit_num = raw_permit.get("permitnum", "")
    portal_link = f"https://services.seattle.gov/portal/customize/LinkToRecord.aspx?altId={permit_num}"
    
    return {
        "permit_num": permit_num,
        "permit_class": raw_permit.get("permitclass"),
        "permit_class_mapped": raw_permit.get("permitclassmapped"),
        "permit_type_mapped": raw_permit.get("permittypemapped"),
        "permit_type_desc": raw_permit.get("permittypedesc"),
        "description": raw_permit.get("description"),
        "est_project_cost": raw_permit.get("estprojectcost"),
        "applied_date": raw_permit.get("applieddate", "")[:10] if raw_permit.get("applieddate") else None,
        "issued_date": raw_permit.get("issueddate", "")[:10] if raw_permit.get("issueddate") else None,
        "status_current": raw_permit.get("statuscurrent"),
        "address": raw_permit.get("originaladdress1"),
        "city": raw_permit.get("originalcity", "Seattle"),
        "state": raw_permit.get("originalstate", "WA"),
        "zipcode": raw_permit.get("originalzip"),
        "contractor_name": raw_permit.get("contractorcompanyname"),
        "latitude": raw_permit.get("latitude"),
        "longitude": raw_permit.get("longitude"),
        "portal_link": portal_link,
        "raw_data": raw_permit,
    }


def determine_owner_builder_status(text: str) -> Optional[bool]:
    """
    Определение статуса owner-builder по тексту.
    
    - Если содержит "Owner" (без "Licensed Contractor") -> True
    - Если содержит "Licensed Contractor" -> False
    - Иначе -> None
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Явный индикатор подрядчика
    if "licensed contractor" in text_lower:
        return False
    
    # Явные индикаторы owner-builder
    owner_keywords = ["owner", "property owner", "self", "homeowner", "owner/lessee"]
    for keyword in owner_keywords:
        if keyword in text_lower:
            return True
    
    return None


async def verify_permit_async(permit_num: str) -> Dict[str, Any]:
    """Асинхронная верификация одного пермита через Accela Portal"""
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
    except ImportError:
        logger.error("Playwright not installed")
        return {
            "permit_num": permit_num,
            "is_owner_builder": None,
            "work_performer_text": None,
            "error": "Playwright not installed"
        }
    
    url = (
        f"{ACCELA_PERMIT_URL}?"
        f"Module=DPD&TabName=DPD&capID1=&capID2=&capID3="
        f"&agencyCode=SEATTLE&IsToShowInspection="
        f"&permitNumber={permit_num}"
    )
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await stealth_async(page)
            
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)  # Задержка
            
            # Ищем текст о том, кто выполняет работы
            work_performer_text = None
            selectors = [
                "text=Who will be performing all the work",
                "text=who will be performing",
                "[id*='ContractorDisclosure']",
                "[id*='WorkPerformer']",
            ]
            
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        parent = await element.evaluate_handle(
                            "el => el.closest('tr') || el.closest('div') || el.parentElement"
                        )
                        if parent:
                            work_performer_text = await parent.inner_text()
                            break
                except Exception:
                    continue
            
            await browser.close()
            
            is_owner = determine_owner_builder_status(work_performer_text)
            
            return {
                "permit_num": permit_num,
                "is_owner_builder": is_owner,
                "work_performer_text": work_performer_text,
                "error": None
            }
            
    except Exception as e:
        logger.error(f"Error verifying {permit_num}: {e}")
        return {
            "permit_num": permit_num,
            "is_owner_builder": None,
            "work_performer_text": None,
            "error": str(e)
        }


def verify_permit_sync(permit_num: str) -> Dict[str, Any]:
    """Синхронная обёртка для верификации"""
    return asyncio.run(verify_permit_async(permit_num))


def parse_permits(
    job_id: int,
    year: int,
    month: Optional[int] = None,
    period: Optional[str] = None,
    permit_class: Optional[str] = None,
    min_cost: float = 5000,
    verify: bool = True
):
    """Основной процесс парсинга пермитов"""
    try:
        update_permit_job(job_id, status="fetching")
        range_desc = f"period={period}" if period else (f"{year}-{month:02d}" if month else str(year))
        logger.info(f"[JOB {job_id}] Starting permit parsing for {range_desc}")
        
        # 1. Получаем данные из API
        try:
            raw_permits = fetch_permits_from_api(
                year=year,
                month=month,
                period=period,
                permit_class=permit_class,
                min_cost=min_cost
            )
        except Exception as api_err:
            err_msg = f"API error: {api_err}"
            logger.error(f"[JOB {job_id}] {err_msg}")
            update_permit_job(
                job_id,
                status="failed",
                error_message=err_msg,
                completed_at=datetime.now().isoformat()
            )
            return
        
        if not raw_permits:
            msg = "No permits found for the selected criteria. Try Last month or a different year (e.g. 2025)."
            logger.warning(f"[JOB {job_id}] {msg}")
            update_permit_job(
                job_id,
                status="completed",
                permits_found=0,
                error_message=msg,
                completed_at=datetime.now().isoformat()
            )
            return
        
        update_permit_job(job_id, status="processing", permits_found=len(raw_permits))
        logger.info(f"[JOB {job_id}] Processing {len(raw_permits)} permits")
        
        # 2. Сохраняем пермиты в БД
        for permit in raw_permits:
            permit_data = extract_permit_data(permit)
            permit_data["job_id"] = job_id
            insert_permit(job_id, permit_data)
        
        # 3. Верификация (если включена)
        owner_builders_count = 0
        verified_count = 0
        
        if verify:
            update_permit_job(job_id, status="verifying")
            logger.info(f"[JOB {job_id}] Starting verification...")
            
            for i, permit in enumerate(raw_permits):
                permit_num = permit.get("permitnum")
                if not permit_num:
                    continue
                
                try:
                    result = verify_permit_sync(permit_num)
                    
                    is_owner = result.get("is_owner_builder")
                    work_text = result.get("work_performer_text")
                    
                    update_permit_verification(permit_num, is_owner, work_text)
                    
                    verified_count += 1
                    if is_owner:
                        owner_builders_count += 1
                    
                    # Обновляем статус каждые 10 записей
                    if (i + 1) % 10 == 0:
                        update_permit_job(
                            job_id,
                            permits_verified=verified_count,
                            owner_builders_found=owner_builders_count
                        )
                        logger.info(f"[JOB {job_id}] Verified {verified_count}/{len(raw_permits)}")
                    
                    # Задержка между запросами
                    import time
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"[JOB {job_id}] Error verifying {permit_num}: {e}")
                    continue
        
        # 4. Завершение
        update_permit_job(
            job_id,
            status="completed",
            permits_found=len(raw_permits),
            permits_verified=verified_count,
            owner_builders_found=owner_builders_count,
            completed_at=datetime.now().isoformat()
        )
        
        logger.info(
            f"[JOB {job_id}] Completed: {len(raw_permits)} permits, "
            f"{verified_count} verified, {owner_builders_count} owner-builders"
        )
        
    except Exception as e:
        err_msg = str(e)
        logger.error(f"[JOB {job_id}] Critical error: {err_msg}")
        import traceback
        logger.error(traceback.format_exc())
        update_permit_job(job_id, status="failed", error_message=err_msg)


def start_permit_parse_job(
    job_id: int,
    year: int,
    month: Optional[int] = None,
    period: Optional[str] = None,
    permit_class: Optional[str] = None,
    min_cost: float = 5000,
    verify: bool = True
):
    """Запускает парсинг пермитов в отдельном потоке"""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        parse_permits,
        job_id=job_id,
        year=year,
        month=month,
        period=period,
        permit_class=permit_class,
        min_cost=min_cost,
        verify=verify
    )
    return future
