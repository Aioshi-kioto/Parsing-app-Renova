"""
Zillow Parser Service
Интеграция с существующим Zillow парсером
"""
import sys
from pathlib import Path
import json
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Добавляем путь к парсерам
PARSERS_PATH = Path(__file__).parent.parent.parent / "parsers" / "zillow-parsing"
sys.path.insert(0, str(PARSERS_PATH / "src"))

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_connection, update_zillow_job, insert_zillow_home

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _parse_price(value):
    """Преобразует цену из строк вроде '$740,000' или '1.00M' в float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        s = value.strip()
        s = s.replace("$", "").replace(",", "")
        # Формат 1.00M
        m = re.match(r"^([0-9]*\.?[0-9]+)m$", s, re.IGNORECASE)
        if m:
            return float(m.group(1)) * 1_000_000
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _parse_city_from_address(address: str) -> str:
    """Извлекает город из полного адреса 'Street, City, ST Zip'"""
    if not address or not isinstance(address, str):
        return ""
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 2:
        return parts[1]  # City между Street и "ST Zip"
    return ""


def extract_home_data(home: Dict[str, Any]) -> Dict[str, Any]:
    """Извлекает данные дома из raw JSON (mapResults + hdpData.homeInfo)"""
    hdp = home.get("hdpData") or {}
    info = hdp.get("homeInfo") or {}
    
    raw_price = home.get("price", home.get("unformattedPrice", info.get("price")))
    price = _parse_price(raw_price)
    
    address = home.get("address") or info.get("streetAddress") or ""
    city = (
        home.get("city") or home.get("addressCity") or info.get("city") or
        _parse_city_from_address(address)
    )
    state = home.get("state") or home.get("addressState") or info.get("state") or ""
    zipcode = home.get("zipcode") or home.get("addressZipcode") or info.get("zipcode") or ""
    
    lat_long = home.get("latLong") or {}
    latitude = home.get("latitude") or lat_long.get("latitude") or info.get("latitude")
    longitude = home.get("longitude") or lat_long.get("longitude") or info.get("longitude") or info.get("long")
    
    detail_url = home.get("detailUrl") or ""
    if detail_url and not detail_url.startswith("http"):
        detail_url = f"https://www.zillow.com{detail_url}" if detail_url.startswith("/") else f"https://www.zillow.com/{detail_url}"
    
    date_sold_ms = info.get("dateSold")
    date_sold = None
    if date_sold_ms:
        try:
            from datetime import datetime
            date_sold = datetime.fromtimestamp(date_sold_ms / 1000).strftime("%Y-%m-%d")
        except (TypeError, OSError):
            pass
    
    return {
        "zpid": str(home.get("zpid", info.get("zpid", ""))),
        "address": address,
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "price": price,
        "price_formatted": home.get("price") if isinstance(home.get("price"), str) else None,
        "beds": home.get("beds") or info.get("bedrooms"),
        "baths": home.get("baths") or info.get("bathrooms"),
        "area_sqft": home.get("area") or info.get("livingArea"),
        "lot_size": home.get("lotSize") or info.get("lotAreaValue"),
        "year_built": home.get("yearBuilt") or info.get("yearBuilt"),
        "home_type": home.get("homeType") or info.get("homeType") or home.get("propertyType"),
        "latitude": latitude,
        "longitude": longitude,
        "date_sold": date_sold,
        "sold_date_text": home.get("flexFieldText"),
        "zestimate": info.get("zestimate"),
        "tax_assessed_value": info.get("taxAssessedValue"),
        "has_image": home.get("hasImage", home.get("imgSrc") is not None),
        "detail_url": detail_url or (f"https://www.zillow.com/homedetails/any-title/{home.get('zpid')}_zpid/" if home.get("zpid") else None),
        "raw_data": home
    }


def save_homes_to_db(job_id: int, homes: List[Dict[str, Any]]) -> int:
    """Сохраняет дома в БД"""
    saved_count = 0
    
    for home in homes:
        home_data = extract_home_data(home)
        zpid = home_data.get("zpid")
        if not zpid:
            continue
        
        try:
            if insert_zillow_home(job_id, home_data):
                saved_count += 1
        except Exception as e:
            logger.error(f"Ошибка при сохранении дома {zpid}: {e}")
    
    return saved_count


def _dedupe_urls(urls: List[str]) -> List[str]:
    """Удаляет дубликаты URL (нормализация + уникальность)."""
    seen = set()
    result = []
    for url in urls:
        u = url.strip()
        if not u or "zillow.com" not in u:
            continue
        # Нормализуем: убираем trailing slash, приводим к нижнему регистру для сравнения
        key = u.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            result.append(u)
    return result


def parse_urls(job_id: int, urls: List[str], headless: bool = False):
    """Парсит список URL и сохраняет результаты в БД"""
    try:
        # Импортируем core модули
        from core.playwright_search import search_from_url_playwright_sync, parse_zillow_url
        from core.tiling import remove_duplicates
        
        def check_cancelled():
            """Проверяет, была ли задача отменена"""
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM zillow_jobs WHERE id = ?", (job_id,))
            result = cursor.fetchone()
            conn.close()
            if result and result[0] == "cancelled":
                raise Exception("Job was cancelled by user")
        
        # Удаляем дубликаты URL перед парсингом
        urls = _dedupe_urls(urls)
        if not urls:
            update_zillow_job(job_id, status="failed", error_message="Нет валидных URL после удаления дубликатов")
            return
        
        # Полностью автоматический режим (без ожидания капчи/Enter)
        update_zillow_job(job_id, status="parsing", current_url_index=0)
        
        all_homes = []
        over_limit_urls: List[str] = []
        
        for url_index, url in enumerate(urls):
            check_cancelled()
            
            logger.info(f"[JOB {job_id}] Парсинг URL {url_index + 1}/{len(urls)}")
            update_zillow_job(
                job_id,
                status="parsing",
                current_url_index=url_index
            )
            
            try:
                # Парсим URL для получения координат и фильтров
                url_data = parse_zillow_url(url)
                
                import os
                proxy_url_env = os.environ.get("PROXY_URL")
                
                # Первый запрос - с капчей
                initial_results = search_from_url_playwright_sync(
                    zillow_url=url,
                    headless=headless,
                    proxy_url=proxy_url_env,
                    slow_mo=800,
                    manual_mode=False,
                    wait_for_manual=False,
                )
                
                map_results = initial_results.get("mapResults", [])
                raw_total = initial_results.get("totalResultCount")
                total_count = raw_total if isinstance(raw_total, int) else None
                
                logger.info(
                    f"[JOB {job_id}] URL {url_index + 1}: получено {len(map_results)} домов, "
                    f"totalResultCount={total_count if total_count is not None else 'N/A'}"
                )
                
                if (total_count == 0) or (total_count is None and len(map_results) == 0):
                    logger.warning(f"[JOB {job_id}] URL {url_index + 1}: нет результатов")
                    continue
                
                # QuadTree нам не нужен: если результатов слишком много — просим заменить URL на более узкий.
                # Надёжное правило: блокируем только если Zillow явно сообщает totalResultCount >= 500.
                if total_count is not None and total_count >= 500:
                    over_limit_urls.append(url)
                    msg = (
                        f"URL returns {total_count} homes (>= 500). "
                        f"Please replace with a narrower Zillow URL (smaller area / more filters).\n"
                        f"{url}"
                    )
                    logger.warning(f"[JOB {job_id}] URL {url_index + 1}: слишком много результатов ({total_count} >= 500). Пропускаем.")
                    update_zillow_job(job_id, error_message=msg)
                    continue

                # Если totalResultCount не пришёл/0, но mapResults ровно 500 — это часто означает "cap".
                # Не стопорим парсинг (по требованию: парсим по ссылкам), но предупреждаем.
                if (total_count is None or total_count == 0) and len(map_results) >= 500:
                    warn_msg = (
                        "Warning: Zillow returned 500 mapResults but totalResultCount is missing/0. "
                        "This URL may be too broad (>500). Consider narrowing it:\n"
                        f"{url}"
                    )
                    update_zillow_job(job_id, error_message=warn_msg)

                # < 500, дедуплицируем результаты
                unique_results = remove_duplicates(map_results)
                logger.info(f"[JOB {job_id}] URL {url_index + 1}: уникальных домов: {len(unique_results)}")
                
                # Добавляем в общий список и дедуплицируем по zpid (между URL могут быть пересечения)
                all_homes.extend(unique_results)
                all_homes = remove_duplicates(all_homes)
                
                # Сохраняем только новые уникальные дома в БД (INSERT OR IGNORE по zpid)
                saved = save_homes_to_db(job_id, unique_results)
                logger.info(f"[JOB {job_id}] URL {url_index + 1}: сохранено {saved} домов в БД, всего уникальных: {len(all_homes)}")
                
                # Обновляем статистику
                update_zillow_job(job_id, homes_found=len(all_homes))
                
            except Exception as e:
                logger.error(f"[JOB {job_id}] Ошибка при парсинге URL {url_index + 1}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                update_zillow_job(job_id, error_message=str(e))
                continue
        
        # Подсчитываем уникальных домов
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT zpid) FROM zillow_homes WHERE job_id = ?", (job_id,))
        unique_count = cursor.fetchone()[0]
        conn.close()
        
        update_zillow_job(
            job_id,
            status="completed",
            homes_found=len(all_homes),
            unique_homes=unique_count,
            completed_at=datetime.now().isoformat()
        )

        # Если были URL с >= 500 — добавим сводку (не падаем целиком, остальные URL уже сохранены)
        if over_limit_urls:
            summary = (
                "Some URLs returned >= 500 homes and were skipped. Replace them with narrower URLs:\n"
                + "\n".join(over_limit_urls[:10])
                + (f"\n... (+{len(over_limit_urls) - 10} more)" if len(over_limit_urls) > 10 else "")
            )
            update_zillow_job(job_id, error_message=summary)
        
        logger.info(f"[JOB {job_id}] Парсинг завершён: {len(all_homes)} домов, {unique_count} уникальных")
        
    except ImportError as e:
        logger.error(f"[JOB {job_id}] Ошибка импорта парсера: {e}")
        update_zillow_job(
            job_id, 
            status="failed", 
            error_message=f"Parser import error: {e}. Make sure zillow-parsing is properly installed."
        )
    except Exception as e:
        err_msg = str(e)
        # Если задача была отменена, не помечаем как failed
        if "cancelled" in err_msg.lower():
            logger.info(f"[JOB {job_id}] Job CANCELLED")
            update_zillow_job(
                job_id,
                status="cancelled",
                completed_at=datetime.now().isoformat()
            )
        else:
            logger.error(f"[JOB {job_id}] Критическая ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            update_zillow_job(job_id, status="failed", error_message=str(e))


def start_zillow_parse_job(job_id: int, urls: List[str], headless: bool = False):
    """Запускает парсинг Zillow в отдельном потоке"""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(parse_urls, job_id, urls, headless)
    return future
