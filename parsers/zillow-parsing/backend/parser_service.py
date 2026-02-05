"""Parser service - обёртка над core для парсинга с сохранением в БД"""
import sys
from pathlib import Path
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Добавляем src в путь для импорта core
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.playwright_search import search_from_url_playwright_sync, parse_zillow_url
from core.tiling import fetch_with_quadtree, remove_duplicates, init_checkpoint
from backend.database import get_connection, dict_factory

logger = logging.getLogger(__name__)


def extract_home_data(home: Dict[str, Any]) -> Dict[str, Any]:
    """Извлекает данные дома из raw JSON"""
    return {
        "zpid": str(home.get("zpid", "")),
        "address": home.get("address", ""),
        "city": home.get("city", ""),
        "state": home.get("state", ""),
        "zipcode": home.get("zipcode", ""),
        "price": home.get("price", None),
        "beds": home.get("beds", None),
        "baths": home.get("baths", None),
        "area_sqft": home.get("area", None),
    }


def save_homes_to_db(job_id: int, homes: List[Dict[str, Any]]):
    """Сохраняет дома в БД"""
    conn = get_connection()
    cursor = conn.cursor()
    
    saved_count = 0
    for home in homes:
        home_data = extract_home_data(home)
        zpid = home_data["zpid"]
        if not zpid:
            continue
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO homes 
                (job_id, zpid, address, city, state, zipcode, price, beds, baths, area_sqft, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                zpid,
                home_data["address"],
                home_data["city"],
                home_data["state"],
                home_data["zipcode"],
                home_data["price"],
                home_data["beds"],
                home_data["baths"],
                home_data["area_sqft"],
                json.dumps(home, ensure_ascii=False)
            ))
            saved_count += 1
        except Exception as e:
            logger.error(f"Ошибка при сохранении дома {zpid}: {e}")
    
    conn.commit()
    conn.close()
    return saved_count


def update_job_status(job_id: int, **kwargs):
    """Обновляет статус job в БД"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(value)
    
    if updates:
        values.append(job_id)
        cursor.execute(f"UPDATE parse_jobs SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
    
    conn.close()


def parse_urls(job_id: int, urls: List[str], status_callback: Optional[Callable] = None):
    """Парсит список URL и сохраняет результаты в БД"""
    try:
        update_job_status(job_id, status="waiting_captcha", current_url_index=0)
        
        all_homes = []
        
        for url_index, url in enumerate(urls):
            logger.info(f"[JOB {job_id}] Парсинг URL {url_index + 1}/{len(urls)}")
            update_job_status(
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
                    filter_state = url_data['filter_state']
                    
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
                update_job_status(job_id, homes_found=len(all_homes))
                
            except Exception as e:
                logger.error(f"[JOB {job_id}] Ошибка при парсинге URL {url_index + 1}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                update_job_status(job_id, error_message=str(e))
                continue
        
        # Подсчитываем уникальных домов
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT zpid) FROM homes WHERE job_id = ?", (job_id,))
        unique_count = cursor.fetchone()[0]
        conn.close()
        
        update_job_status(
            job_id,
            status="completed",
            homes_found=len(all_homes),
            unique_homes=unique_count,
            completed_at=datetime.now().isoformat()
        )
        
        logger.info(f"[JOB {job_id}] Парсинг завершён: {len(all_homes)} домов, {unique_count} уникальных")
        
    except Exception as e:
        logger.error(f"[JOB {job_id}] Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        update_job_status(job_id, status="failed", error_message=str(e))


def start_parse_job(job_id: int, urls: List[str]):
    """Запускает парсинг в отдельном потоке"""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(parse_urls, job_id, urls)
    return future
