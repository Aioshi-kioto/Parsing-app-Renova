"""
Permit Parser Service
Интеграция с Seattle Building Permits парсером
"""
import os
import sys
from pathlib import Path
import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# На Windows subprocess в asyncio работает только с ProactorEventLoop.
# Верификация запускается в фоновом потоке; без этой политики asyncio.run()
# создаёт loop без поддержки subprocess → NotImplementedError у Playwright.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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

# Верификация: настраиваемые лимиты и задержки (ускорить можно, но риск rate-limit или падений)
def _verify_batch_size() -> int:
    """Размер батча (параллельных браузеров). 4–6 обычно ок, 8 — только при хорошем железе."""
    n = int(os.environ.get("PERMIT_VERIFY_BATCH_SIZE", "6"))
    return max(1, min(n, 8))


VERIFY_DELAY_AFTER_LOAD = 1.2   # сек после загрузки страницы (меньше = быстрее, но возможны пропуски DOM)
VERIFY_DELAY_AFTER_EXPAND = 0.8 # сек после клика Expand (чтобы CONTRACTOR DISCLOSURE успел отрендериться)
VERIFY_DELAY_BETWEEN_BATCHES = 0.4  # сек между батчами (снижает нагрузку на портал)


# Accela Portal — используем тот же URL, что и у пользователя (services.seattle.gov),
# чтобы DOM совпадал с блоком "Who will be performing all the work?" / Owner/Lessee
def portal_link_for_permit(permit_num: str) -> str:
    return f"https://services.seattle.gov/portal/customize/LinkToRecord.aspx?altId={permit_num}"


def _get_date_range(year: int, month: Optional[int] = None) -> tuple:
    """Возвращает (date_from, date_to) для запроса"""
    if month is not None and 1 <= month <= 12:
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
    permit_class: Optional[str] = None,
    permit_type: str = "Building",
    contractor_is_null: bool = True,
    min_cost: float = 5000,
    limit: int = 10000,
    offset: int = 0,
) -> Dict[str, str]:
    """Построение SoQL запроса для фильтрации пермитов"""
    print(f"[BUILD SOQL] Building query: year={year}, month={month}, permit_class={permit_class}")
    try:
        conditions = []
        
        date_from, date_to = _get_date_range(year, month)
        print(f"[BUILD SOQL] Date range: {date_from} to {date_to}")
        conditions.append(f"applieddate >= '{date_from}'")
        conditions.append(f"applieddate < '{date_to}'")
        
        # Фильтр по классу пермита
        if permit_class and permit_class.strip():
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
        
        print(f"[BUILD SOQL] Final WHERE clause: {where_clause}")
        print(f"[BUILD SOQL] Query params: {params}")
        return params
    except Exception as e:
        print(f"[BUILD SOQL] ✗ Error building SOQL query: {e}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Error building SOQL query: {e}")
        raise


def fetch_permits_from_api(
    year: int = 2026,
    month: Optional[int] = None,
    permit_class: Optional[str] = None,
    min_cost: float = 5000,
    limit: int = 10000,
) -> List[Dict[str, Any]]:
    """Получение пермитов из Seattle Open Data API"""
    try:
        base_url = f"https://{SOCRATA_CONFIG['domain']}/resource/{SOCRATA_CONFIG['dataset_id']}.json"
        
        params = build_soql_query(
            year=year,
            month=month,
            permit_class=permit_class,
            min_cost=min_cost,
            limit=limit,
        )
        
        logger.info(f"Fetching permits from {base_url}")
        logger.info(f"Query params: {params}")
        logger.info(f"Query WHERE: {params.get('$where', 'N/A')}")
        
        with httpx.Client(timeout=60.0) as client:
            response = client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
        
        logger.info(f"Fetched {len(data)} permits")
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching permits: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error fetching permits from API: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def extract_permit_data(raw_permit: Dict[str, Any]) -> Dict[str, Any]:
    """Извлечение структурированных данных из raw API response"""
    permit_num = raw_permit.get("permitnum", "")
    portal_link = portal_link_for_permit(permit_num)
    
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
    Определение статуса owner-builder по тексту (Contractor Disclosure).
    
    - Если содержит "Owner" (без "Licensed Contractor") -> True
    - Если содержит "Licensed Contractor" -> False
    - Иначе -> None
    """
    if not text or not str(text).strip():
        return None
    
    text_lower = str(text).lower().strip()
    
    # Явный индикатор подрядчика (приоритет)
    if "licensed contractor" in text_lower or "contractor license" in text_lower:
        return False
    
    # Явные индикаторы owner-builder (master_spec.md 5.3)
    owner_keywords = [
        "owner", "property owner", "self", "homeowner", "owner/lessee",
        "owner-builder", "owner builder", "owner/ builder"
    ]
    for keyword in owner_keywords:
        if keyword in text_lower:
            return True
    
    return None


def _check_job_cancelled(job_id: Optional[int]) -> bool:
    """Проверка, отменён ли джоб. Возвращает True если отменён."""
    if job_id is None:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM permit_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == "cancelled"


async def verify_permit_async(
    permit_num: str, headless: bool = False, job_id: Optional[int] = None
) -> Dict[str, Any]:
    """Асинхронная верификация одного пермита через Accela Portal.
    Если передан job_id и джоб отменён — браузер не открывается, возвращаем error.
    Во время верификации проверяет cancelled и закрывает браузер если джоб отменён.
    """
    # Проверка ПЕРЕД открытием браузера
    if _check_job_cancelled(job_id):
        return {
            "permit_num": permit_num,
            "is_owner_builder": None,
            "work_performer_text": None,
            "error": "Job cancelled",
        }
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        logger.error("Playwright not installed: %s. Run: pip install playwright && playwright install chromium", e)
        return {
            "permit_num": permit_num,
            "is_owner_builder": None,
            "work_performer_text": None,
            "error": "Playwright not installed. Run: pip install playwright && playwright install chromium"
        }
    
    # Тот же URL, что открывает пользователь — страница с блоком Contractor Disclosure
    url = portal_link_for_permit(permit_num)
    
    logger.info(f"[Verify] {permit_num}: Starting verification (headless={headless}, browser visible when False)")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            # Stealth опционально (playwright_stealth v2.x убрал stealth_async)
            try:
                from playwright_stealth import Stealth
                stealth = Stealth()
                if hasattr(stealth, "apply_stealth_async"):
                    await stealth.apply_stealth_async(context)
            except Exception:
                pass
            page = await context.new_page()
            
            # Проверка cancelled после открытия браузера
            if _check_job_cancelled(job_id):
                logger.info(f"[Verify] {permit_num}: Job cancelled, closing browser")
                await browser.close()
                return {
                    "permit_num": permit_num,
                    "is_owner_builder": None,
                    "work_performer_text": None,
                    "error": "Job cancelled",
                }
            
            await page.goto(url, timeout=30000)
            
            # Проверка cancelled после загрузки страницы
            if _check_job_cancelled(job_id):
                logger.info(f"[Verify] {permit_num}: Job cancelled after page load, closing browser")
                await browser.close()
                return {
                    "permit_num": permit_num,
                    "is_owner_builder": None,
                    "work_performer_text": None,
                    "error": "Job cancelled",
                }
            
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(VERIFY_DELAY_AFTER_LOAD)
            
            # Раскрыть "More Details" / "Application Information", чтобы блок CONTRACTOR DISCLOSURE был в DOM
            try:
                expand = page.get_by_text("Expand More Details", exact=False).or_(page.get_by_text("Expand Application Information", exact=False))
                if await expand.count() > 0:
                    await expand.first.click()
                    await asyncio.sleep(VERIFY_DELAY_AFTER_EXPAND)
            except Exception:
                pass
            
            if _check_job_cancelled(job_id):
                logger.info(f"[Verify] {permit_num}: Job cancelled before search, closing browser")
                await browser.close()
                return {
                    "permit_num": permit_num,
                    "is_owner_builder": None,
                    "work_performer_text": None,
                    "error": "Job cancelled",
                }
            
            # Блок CONTRACTOR DISCLOSURE (одинаковая структура для обоих случаев):
            # — Owner/Lessee: Col1 "Who will be performing...?" → Col2 "Owner/Lessee"; далее только "I have submitted...". Строки Contractor License нет.
            # — Licensed Contractor: Col1 "Who will be performing...?" → Col2 "Licensed Contractor"; Col1 "Contractor License:" → Col2 "MIOVIRA871J4".
            # Ищем заголовок CONTRACTOR DISCLOSURE, затем пару Col1/Col2 с "Who will be performing all the work?".
            result_js = await page.evaluate("""() => {
                const out = { workPerformer: null, contractorLicense: null };
                const whoText = 'Who will be performing all the work';
                const licenseText = 'Contractor License';
                const titles = document.querySelectorAll('.MoreDetail_ItemTitle');
                let disclosureBlock = null;
                for (const t of titles) {
                    if ((t.textContent || '').trim() === 'CONTRACTOR DISCLOSURE') {
                        disclosureBlock = t.parentElement;
                        break;
                    }
                }
                const scope = disclosureBlock || document.body;
                const col1s = scope.querySelectorAll('.MoreDetail_ItemCol1');
                for (const col1 of col1s) {
                    const label = (col1.textContent || '').trim();
                    if (label.indexOf(whoText) === 0) {
                        const col2 = col1.nextElementSibling && col1.nextElementSibling.classList.contains('MoreDetail_ItemCol2')
                            ? col1.nextElementSibling
                            : null;
                        if (col2) out.workPerformer = (col2.innerText || '').trim();
                        break;
                    }
                }
                for (const col1 of col1s) {
                    const label = (col1.textContent || '').trim();
                    if (label.indexOf(licenseText) === 0) {
                        const col2 = col1.nextElementSibling && col1.nextElementSibling.classList.contains('MoreDetail_ItemCol2')
                            ? col1.nextElementSibling
                            : null;
                        if (col2) out.contractorLicense = (col2.innerText || '').trim();
                        break;
                    }
                }
                return out;
            }""")
            
            work_performer_text = (result_js or {}).get("workPerformer") or ""
            contractor_license = (result_js or {}).get("contractorLicense") or ""
            work_performer_text = work_performer_text.strip() if work_performer_text else ""
            
            # Решение только по значению из блока "Who will be performing all the work?"
            if work_performer_text.lower().startswith("owner") and "lessee" in work_performer_text.lower():
                is_owner = True
                work_performer_text = work_performer_text.split("\n")[0].strip() or "Owner/Lessee"
            elif "licensed contractor" in work_performer_text.lower():
                is_owner = False
                work_performer_text = work_performer_text.split("\n")[0].strip() or "Licensed Contractor"
            else:
                is_owner = False
                if not work_performer_text:
                    work_performer_text = "Not found"
            
            await browser.close()
            
            portal_link = portal_link_for_permit(permit_num)
            logger.info(
                f"[Verify] {permit_num} | {portal_link} | "
                f"Who will be performing: '{work_performer_text}' | Contractor License: '{contractor_license}' | is_owner={is_owner}"
            )
            
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


def verify_permit_sync(
    permit_num: str, headless: bool = False, job_id: Optional[int] = None
) -> Dict[str, Any]:
    """Синхронная обёртка для верификации. job_id нужен для проверки отмены до запуска браузера."""
    return asyncio.run(verify_permit_async(permit_num, headless=headless, job_id=job_id))


async def verify_permits_batch_async(
    permit_nums: List[str],
    headless: bool = False,
    job_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Верификация нескольких пермитов параллельно (каждый в своём браузере)."""
    if not permit_nums:
        return []
    tasks = [verify_permit_async(pn, headless=headless, job_id=job_id) for pn in permit_nums]
    return await asyncio.gather(*tasks, return_exceptions=False)


def parse_permits(
    job_id: int,
    year: int,
    month: Optional[int] = None,
    permit_class: Optional[str] = None,
    min_cost: float = 5000,
    verify: bool = True,
    headless: bool = False
):
    """Основной процесс парсинга пермитов"""
    print(f"\n[PERMIT PARSER] ===== Starting parse_permits for JOB {job_id} =====")
    print(f"[PERMIT PARSER] Year: {year}, Month: {month}, Permit Class: {permit_class}")
    print(f"[PERMIT PARSER] Min Cost: {min_cost}, Verify: {verify}, Headless: {headless} (browser visible when headless=False)")
    
    def check_cancelled():
        """Проверяет, была ли задача отменена"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM permit_jobs WHERE id = ?", (job_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0] == "cancelled":
            raise Exception("Job was cancelled by user")
    
    try:
        print(f"[PERMIT PARSER] Updating job status to 'fetching'...")
        update_permit_job(job_id, status="fetching")
        range_desc = f"{year}-{month:02d}" if month else str(year)
        print(f"[PERMIT PARSER] Range description: {range_desc}")
        logger.info(f"[JOB {job_id}] Starting permit parsing for {range_desc}")
        
        # 1. Получаем данные из API
        print(f"[PERMIT PARSER] Fetching permits from API...")
        try:
            raw_permits = fetch_permits_from_api(
                year=year,
                month=month,
                permit_class=permit_class,
                min_cost=min_cost
            )
            print(f"[PERMIT PARSER] OK Fetched {len(raw_permits)} permits from API")
            check_cancelled()
            # Сразу обновляем счётчик, чтобы UI показал "Permits Found"
            update_permit_job(job_id, status="processing", permits_found=len(raw_permits))
        except Exception as api_err:
            err_msg = f"API error: {api_err}"
            print(f"[PERMIT PARSER] ERROR API Error: {err_msg}")
            import traceback
            print(f"[PERMIT PARSER] Traceback:\n{traceback.format_exc()}")
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
        
        logger.info(f"[JOB {job_id}] Processing {len(raw_permits)} permits")
        
        # 2. Сохраняем пермиты в БД
        for i, permit in enumerate(raw_permits):
            if i % 50 == 0:
                check_cancelled()
            permit_data = extract_permit_data(permit)
            permit_data["job_id"] = job_id
            insert_permit(job_id, permit_data)
        
        # 3. Верификация (если включена) — батчами параллельно (размер через PERMIT_VERIFY_BATCH_SIZE, по умолч. 6)
        owner_builders_count = 0
        verified_count = 0
        batch_size = _verify_batch_size()
        
        if verify:
            permit_nums = [p.get("permitnum") for p in raw_permits if p.get("permitnum")]
            update_permit_job(job_id, status="verifying", permits_found=len(permit_nums))
            logger.info(f"[JOB {job_id}] Starting verification ({len(permit_nums)} permits, batch size {batch_size})...")
            
            batch_start = 0
            while batch_start < len(permit_nums):
                check_cancelled()
                batch = permit_nums[batch_start : batch_start + batch_size]
                batch_start += len(batch)
                
                try:
                    results = asyncio.run(verify_permits_batch_async(batch, headless=headless, job_id=job_id))
                except Exception as e:
                    logger.error(f"[JOB {job_id}] Batch verification error: {e}")
                    for permit_num in batch:
                        update_permit_verification(permit_num, None, None, verification_error=str(e)[:200])
                    verified_count += len(batch)
                    batch_start = len(permit_nums)
                    continue
                
                for result in results:
                    permit_num = result.get("permit_num")
                    is_owner = result.get("is_owner_builder")
                    work_text = result.get("work_performer_text")
                    err = result.get("error")
                    
                    if err == "Job cancelled":
                        logger.info(f"[JOB {job_id}] Verification stopped (job cancelled)")
                        batch_start = len(permit_nums)
                        break
                    
                    update_permit_verification(
                        permit_num, is_owner, work_text,
                        verification_error=err if err else None
                    )
                    verified_count += 1
                    if is_owner:
                        owner_builders_count += 1
                
                if any(r.get("error") == "Job cancelled" for r in results):
                    break
                
                update_permit_job(
                    job_id,
                    permits_verified=verified_count,
                    owner_builders_found=owner_builders_count
                )
                logger.info(f"[JOB {job_id}] Verified {verified_count}/{len(permit_nums)}")
                
                import time
                time.sleep(VERIFY_DELAY_BETWEEN_BATCHES)
        
        # 4. Завершение (не перезаписываем status=cancelled, если джоб отменили)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM permit_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        final_status = "completed" if (not row or row[0] != "cancelled") else "cancelled"
        update_permit_job(
            job_id,
            status=final_status,
            permits_found=len(raw_permits),
            permits_verified=verified_count,
            owner_builders_found=owner_builders_count,
            completed_at=datetime.now().isoformat()
        )
        logger.info(
            f"[JOB {job_id}] {final_status}: {len(raw_permits)} permits, "
            f"{verified_count} verified, {owner_builders_count} owner-builders"
        )
        
    except Exception as e:
        err_msg = str(e)
        import traceback
        error_traceback = traceback.format_exc()
        
        # Если задача была отменена, не помечаем как failed
        if "cancelled" in err_msg.lower():
            print(f"[PERMIT PARSER] Job {job_id} CANCELLED")
            update_permit_job(
                job_id,
                status="cancelled",
                completed_at=datetime.now().isoformat(),
            )
        else:
            print(f"\n[PERMIT PARSER] CRITICAL ERROR in JOB {job_id}")
            print(f"[PERMIT PARSER] {err_msg}")
            print(f"[PERMIT PARSER] Traceback:\n{error_traceback}")
            print(f"[PERMIT PARSER] ============================================\n")
            
            logger.error(f"[JOB {job_id}] Critical error: {err_msg}")
            logger.error(error_traceback)
            update_permit_job(job_id, status="failed", error_message=err_msg)


def start_permit_parse_job(
    job_id: int,
    year: int,
    month: Optional[int] = None,
    permit_class: Optional[str] = None,
    min_cost: float = 5000,
    verify: bool = True,
    headless: bool = False
):
    """Запускает парсинг пермитов в отдельном потоке"""
    print(f"[PERMIT PARSER] Starting background thread for job {job_id}...")
    try:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            parse_permits,
            job_id=job_id,
            year=year,
            month=month,
            permit_class=permit_class,
            min_cost=min_cost,
            verify=verify,
            headless=headless
        )
        print(f"[PERMIT PARSER] OK Background thread started for job {job_id}")
        return future
    except Exception as e:
        print(f"[PERMIT PARSER] ERROR starting background thread: {e}")
        import traceback
        print(traceback.format_exc())
        raise
