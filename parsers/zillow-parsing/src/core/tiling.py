from typing import List, Dict, Any, Tuple, Optional
import logging
import json
import os
from datetime import datetime
from core.playwright_search import search_sold_playwright_sync
from core.search import sold

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Глобальные переменные для checkpoint
_checkpoint_file: Optional[str] = None
_checkpoint_data: Dict[str, Any] = {}


def divide_region(north: float, south: float, west: float, east: float) -> List[Tuple[float, float, float, float]]:
    """Делит область на 4 квадрата (QuadTree разбиение)
    
    Args:
        north: Северная граница (latitude)
        south: Южная граница (latitude)
        west: Западная граница (longitude)
        east: Восточная граница (longitude)
    
    Returns:
        Список из 4 кортежей: [(north, south, west, east), ...]
    """
    mid_lat = (north + south) / 2.0
    mid_long = (west + east) / 2.0
    
    return [
        (north, mid_lat, west, mid_long),      # Северо-запад
        (north, mid_lat, mid_long, east),      # Северо-восток
        (mid_lat, south, west, mid_long),     # Юго-запад
        (mid_lat, south, mid_long, east),     # Юго-восток
    ]


def init_checkpoint(checkpoint_file: str = "scraping_checkpoint.json"):
    """Инициализирует систему checkpoint
    
    Args:
        checkpoint_file: Путь к файлу checkpoint
    """
    global _checkpoint_file, _checkpoint_data
    _checkpoint_file = checkpoint_file
    
    # Загружаем существующий checkpoint, если есть
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                _checkpoint_data = json.load(f)
            logger.info(f"[CHECKPOINT] Загружен checkpoint: {len(_checkpoint_data.get('processed_tiles', []))} обработанных областей, {len(_checkpoint_data.get('found_zpids', []))} найденных домов")
        except Exception as e:
            logger.warning(f"[CHECKPOINT] Ошибка при загрузке checkpoint: {e}, начинаем с нуля")
            _checkpoint_data = {"processed_tiles": [], "found_zpids": set()}
    else:
        _checkpoint_data = {"processed_tiles": [], "found_zpids": set()}
        logger.info(f"[CHECKPOINT] Создан новый checkpoint файл: {checkpoint_file}")


def save_checkpoint():
    """Сохраняет текущее состояние checkpoint"""
    global _checkpoint_file, _checkpoint_data
    if not _checkpoint_file:
        return
    
    try:
        # Преобразуем set в list для JSON
        checkpoint_to_save = {
            "processed_tiles": _checkpoint_data.get("processed_tiles", []),
            "found_zpids": list(_checkpoint_data.get("found_zpids", set())),
            "last_updated": str(datetime.now().isoformat()) if 'datetime' in globals() else None
        }
        
        with open(_checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_to_save, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"[CHECKPOINT] Сохранен checkpoint: {len(checkpoint_to_save['processed_tiles'])} областей, {len(checkpoint_to_save['found_zpids'])} домов")
    except Exception as e:
        logger.error(f"[CHECKPOINT] Ошибка при сохранении checkpoint: {e}")


def is_tile_processed(north: float, south: float, west: float, east: float, zoom: int) -> bool:
    """Проверяет, была ли уже обработана эта область
    
    Args:
        north, south, west, east: Координаты области
        zoom: Уровень зума
    
    Returns:
        True если область уже обработана
    """
    global _checkpoint_data
    tile_key = f"{north:.6f},{south:.6f},{west:.6f},{east:.6f},{zoom}"
    processed = tile_key in _checkpoint_data.get("processed_tiles", [])
    if processed:
        logger.info(f"[CHECKPOINT] Область уже обработана, пропускаем: {tile_key}")
    return processed


def mark_tile_processed(north: float, south: float, west: float, east: float, zoom: int):
    """Отмечает область как обработанную"""
    global _checkpoint_data
    tile_key = f"{north:.6f},{south:.6f},{west:.6f},{east:.6f},{zoom}"
    if "processed_tiles" not in _checkpoint_data:
        _checkpoint_data["processed_tiles"] = []
    if tile_key not in _checkpoint_data["processed_tiles"]:
        _checkpoint_data["processed_tiles"].append(tile_key)
        save_checkpoint()


def add_found_zpids(zpids: List[int]):
    """Добавляет найденные zpids в checkpoint"""
    global _checkpoint_data
    if "found_zpids" not in _checkpoint_data:
        _checkpoint_data["found_zpids"] = set()
    _checkpoint_data["found_zpids"].update(zpids)
    save_checkpoint()


def get_checkpoint_stats() -> Dict[str, Any]:
    """Возвращает статистику checkpoint"""
    global _checkpoint_data
    return {
        "processed_tiles": len(_checkpoint_data.get("processed_tiles", [])),
        "found_zpids": len(_checkpoint_data.get("found_zpids", set())),
    }


def remove_duplicates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Удаляет дубликаты по zpid (property ID)
    
    Args:
        results: Список объектов недвижимости
    
    Returns:
        Список уникальных объектов (по zpid)
    """
    seen_zpids = set()
    unique_results = []
    
    for house in results:
        zpid = house.get("zpid")
        if zpid and zpid not in seen_zpids:
            seen_zpids.add(zpid)
            unique_results.append(house)
    
    return unique_results


def fetch_with_quadtree(
    north: float,
    south: float,
    west: float,
    east: float,
    zoom: int,
    filters: Dict[str, Any],
    proxy_url: str | None = None,
    cookies: Dict[str, str] | None = None,
    max_depth: int = 10,
    current_depth: int = 0,
    use_playwright: bool = True,
    headless: bool = True,
    checkpoint_file: str | None = None,
    result_limit: int = 200,  # Лимит для разбиения (200 для безопасности, вместо 500)
) -> List[Dict[str, Any]]:
    """Рекурсивная функция для парсинга с QuadTree разбиением
    
    Если totalResultCount >= result_limit (по умолчанию 200), область делится на 4 квадрата и процесс повторяется рекурсивно.
    
    Args:
        north: Северная граница (latitude)
        south: Южная граница (latitude)
        west: Западная граница (longitude)
        east: Восточная граница (longitude)
        zoom: Уровень зума карты
        filters: Словарь с параметрами фильтров
        proxy_url: URL прокси (опционально)
        cookies: Cookies для обхода блокировок (опционально, не используется с Playwright)
        max_depth: Максимальная глубина рекурсии (защита от бесконечной рекурсии)
        current_depth: Текущая глубина рекурсии
        use_playwright: Использовать Playwright вместо API (рекомендуется)
        headless: Запускать браузер в headless режиме
        checkpoint_file: Путь к файлу checkpoint для сохранения прогресса
        result_limit: Лимит результатов для разбиения (по умолчанию 200 для безопасности)
    
    Returns:
        Список уникальных объектов недвижимости
    """
    # Инициализируем checkpoint при первом вызове
    global _checkpoint_file
    if checkpoint_file and not _checkpoint_file:
        init_checkpoint(checkpoint_file)
    
    # Проверяем, не обработана ли уже эта область
    if _checkpoint_file and is_tile_processed(north, south, west, east, zoom):
        return []
    
    if current_depth >= max_depth:
        logger.warning(f"[QUADTREE] Достигнута максимальная глубина рекурсии ({max_depth}) для области: N={north:.4f}, S={south:.4f}, W={west:.4f}, E={east:.4f}")
        return []
    
    logger.info(f"[QUADTREE] [Depth {current_depth}] Обработка области: N={north:.4f}, S={south:.4f}, W={west:.4f}, E={east:.4f}")
    
    # Выполняем запрос к области
    try:
        if use_playwright:
            logger.info(f"[QUADTREE] Использование Playwright для запроса...")
            # Используем медленный режим для избежания блокировок
            results = search_sold_playwright_sync(
                north=north,
                south=south,
                west=west,
                east=east,
                zoom=zoom,
                filters=filters,
                headless=headless,
                proxy_url=proxy_url,
                slow_mo=2000,  # 2 секунды между действиями (оптимизировано)
                manual_mode=False,  # Автоматический режим (без пауз)
                wait_for_manual=False,  # Без ожидания Enter
            )
        else:
            logger.info(f"[QUADTREE] Использование API для запроса...")
            results = sold(
                pagination=1,
                search_value="",
                min_beds=None,
                max_beds=None,
                min_bathrooms=None,
                max_bathrooms=None,
                min_price=filters.get("min_price", None),
                max_price=None,
                ne_lat=north,
                ne_long=east,
                sw_lat=south,
                sw_long=west,
                zoom_value=zoom,
                proxy_url=proxy_url,
                basement_unfinished=filters.get("basement_unfinished", False),
                home_type_houses=filters.get("home_type_houses", False),
                sold_in_last_months=filters.get("sold_in_last_months", None),
                cookies=cookies,
            )
        
        # Получаем mapResults и totalResultCount
        map_results = results.get("mapResults", [])
        total_count = results.get("totalResultCount", len(map_results))
        
        # Извлекаем zpids для checkpoint
        zpids = [h.get("zpid") for h in map_results if h.get("zpid")]
        if zpids and _checkpoint_file:
            add_found_zpids(zpids)
        
        logger.info(f"[QUADTREE] [Depth {current_depth}] Результаты: totalResultCount={total_count}, mapResults={len(map_results)}")
        
        # Отмечаем область как обработанную
        if _checkpoint_file:
            mark_tile_processed(north, south, west, east, zoom)
        
        # Если результатов >= result_limit, нужно разбить область
        if total_count >= result_limit:
            logger.warning(f"[QUADTREE] [Depth {current_depth}] Лимит достигнут ({total_count} >= {result_limit}), разбиваем область на 4 квадрата...")
            
            # Делим область на 4 квадрата
            sub_regions = divide_region(north, south, west, east)
            
            # Рекурсивно обрабатываем каждый квадрат
            all_results = []
            for i, (sub_north, sub_south, sub_west, sub_east) in enumerate(sub_regions, 1):
                logger.info(f"[QUADTREE] [Depth {current_depth}] Обработка квадрата {i}/4...")
                sub_results = fetch_with_quadtree(
                    north=sub_north,
                    south=sub_south,
                    west=sub_west,
                    east=sub_east,
                    zoom=zoom,
                    filters=filters,
                    proxy_url=proxy_url,
                    cookies=cookies,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    use_playwright=use_playwright,
                    headless=headless,
                    checkpoint_file=checkpoint_file,
                    result_limit=result_limit,
                )
                all_results.extend(sub_results)
                logger.info(f"[QUADTREE] [Depth {current_depth}] Квадрат {i}/4: получено {len(sub_results)} домов")
            
            # Удаляем дубликаты и возвращаем
            unique_results = remove_duplicates(all_results)
            logger.info(f"[QUADTREE] [Depth {current_depth}] Объединено {len(all_results)} результатов, уникальных: {len(unique_results)}")
            return unique_results
        
        else:
            # Результатов < 500, возвращаем как есть
            logger.info(f"[QUADTREE] [Depth {current_depth}] Результатов < 500, возвращаем {len(map_results)} домов")
            return map_results
    
    except Exception as e:
        logger.error(f"[QUADTREE] [Depth {current_depth}] Ошибка при запросе к области: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []
