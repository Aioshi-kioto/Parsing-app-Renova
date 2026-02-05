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


def extract_home_data(home: Dict[str, Any]) -> Dict[str, Any]:
    """Извлекает данные дома из raw JSON"""
    return {
        "zpid": str(home.get("zpid", "")),
        "address": home.get("address", home.get("streetAddress", "")),
        "city": home.get("city", home.get("addressCity", "")),
        "state": home.get("state", home.get("addressState", "")),
        "zipcode": home.get("zipcode", home.get("addressZipcode", "")),
        "price": home.get("price", home.get("unformattedPrice", None)),
        "beds": home.get("beds", home.get("bedrooms", None)),
        "baths": home.get("baths", home.get("bathrooms", None)),
        "area_sqft": home.get("area", home.get("livingArea", None)),
        "lot_size": home.get("lotSize", home.get("lotAreaValue", None)),
        "year_built": home.get("yearBuilt", None),
        "home_type": home.get("homeType", home.get("propertyType", None)),
        "latitude": home.get("latitude", home.get("lat", None)),
        "longitude": home.get("longitude", home.get("lng", home.get("long", None))),
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


def parse_urls(job_id: int, urls: List[str]):
    """Парсит список URL и сохраняет результаты в БД"""
    try:
        # Импортируем core модули
        from core.playwright_search import search_from_url_playwright_sync, parse_zillow_url
        from core.tiling import fetch_with_quadtree, remove_duplicates, init_checkpoint
        
        update_zillow_job(job_id, status="waiting_captcha", current_url_index=0)
        
        all_homes = []
        
        for url_index, url in enumerate(urls):
            logger.info(f"[JOB {job_id}] Парсинг URL {url_index + 1}/{len(urls)}")
            update_zillow_job(
                job_id,
                status="parsing",
                current_url_index=url_index
            )
            
            # Первый URL - с капчей, остальные - без
            is_first = (url_index == 0)
            
            try:
                # Парсим URL для получения координат и фильтров
                url_data = parse_zillow_url(url)
                
                # Первый запрос - с капчей
                initial_results = search_from_url_playwright_sync(
                    zillow_url=url,
                    headless=False,
                    proxy_url=None,
                    slow_mo=3000,
                    manual_mode=is_first,
                    wait_for_manual=is_first,
                )
                
                map_results = initial_results.get("mapResults", [])
                total_count = initial_results.get("totalResultCount", len(map_results))
                
                logger.info(f"[JOB {job_id}] URL {url_index + 1}: получено {len(map_results)} домов, totalResultCount={total_count}")
                
                if total_count == 0:
                    logger.warning(f"[JOB {job_id}] URL {url_index + 1}: нет результатов")
                    continue
                
                # Если >= 500, используем QuadTree
                if total_count >= 500:
                    logger.info(f"[JOB {job_id}] URL {url_index + 1}: {total_count} >= 500, используем QuadTree")
                    
                    # Преобразуем filter_state в формат для tiling
                    filters = {}
                    filter_state = url_data.get('filter_state', {})
                    
                    if filter_state.get("basement", {}).get("value") == ["unfinished"]:
                        filters["basement_unfinished"] = True
                    if filter_state.get("homeType", {}).get("value") == ["HOUSE"]:
                        filters["home_type_houses"] = True
                    if "price" in filter_state and "min" in filter_state["price"]:
                        filters["min_price"] = filter_state["price"]["min"]
                    if "daysOnZillow" in filter_state and "max" in filter_state["daysOnZillow"]:
                        filters["sold_in_last_months"] = filter_state["daysOnZillow"]["max"] // 30
                    
                    # Используем отдельный checkpoint для каждого job
                    checkpoint_file = f"scraping_checkpoint_job_{job_id}.json"
                    init_checkpoint(checkpoint_file)
                    
                    # QuadTree разбиение
                    quadtree_results = fetch_with_quadtree(
                        north=url_data['north'],
                        south=url_data['south'],
                        west=url_data['west'],
                        east=url_data['east'],
                        zoom=url_data['zoom'],
                        filters=filters,
                        proxy_url=None,
                        use_playwright=True,
                        headless=False,
                        checkpoint_file=checkpoint_file,
                    )
                    
                    unique_results = remove_duplicates(quadtree_results)
                    logger.info(f"[JOB {job_id}] URL {url_index + 1}: QuadTree завершён, уникальных домов: {len(unique_results)}")
                    all_homes.extend(unique_results)
                else:
                    # < 500, сохраняем как есть
                    unique_results = remove_duplicates(map_results)
                    logger.info(f"[JOB {job_id}] URL {url_index + 1}: уникальных домов: {len(unique_results)}")
                    all_homes.extend(unique_results)
                
                # Сохраняем дома в БД
                saved = save_homes_to_db(job_id, unique_results)
                logger.info(f"[JOB {job_id}] URL {url_index + 1}: сохранено {saved} домов в БД")
                
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
        
        logger.info(f"[JOB {job_id}] Парсинг завершён: {len(all_homes)} домов, {unique_count} уникальных")
        
    except ImportError as e:
        logger.error(f"[JOB {job_id}] Ошибка импорта парсера: {e}")
        update_zillow_job(
            job_id, 
            status="failed", 
            error_message=f"Parser import error: {e}. Make sure zillow-parsing is properly installed."
        )
    except Exception as e:
        logger.error(f"[JOB {job_id}] Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        update_zillow_job(job_id, status="failed", error_message=str(e))


def start_zillow_parse_job(job_id: int, urls: List[str]):
    """Запускает парсинг Zillow в отдельном потоке"""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(parse_urls, job_id, urls)
    return future
