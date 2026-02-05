import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для импортов
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

"""
Скрипт для парсинга Seattle по готовым URL
Обрабатывает список URL по очереди и собирает все результаты
"""

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import List, Dict, Any
from core.playwright_search import search_from_url_playwright_sync
from core.tiling import remove_duplicates

# Настройка логирования
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, f"parse_seattle_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)


def parse_url(url: str, part_number: int, total_parts: int, headless: bool = False, manual_mode: bool = True) -> List[Dict[str, Any]]:
    """
    Парсит один URL
    
    Args:
        url: URL для парсинга
        part_number: Номер части (для логирования)
        total_parts: Всего частей
        headless: Запускать браузер в headless режиме
        manual_mode: Пауза для капчи (только для первой части)
    
    Returns:
        Список найденных домов
    """
    logger.info("=" * 80)
    logger.info(f"SEATTLE - ЧАСТЬ {part_number}/{total_parts}")
    logger.info("=" * 80)
    
    try:
        logger.info(f"[SEARCH] Запрос к Zillow для части {part_number}...")
        logger.info(f"[URL] {url[:150]}...")
        
        results = search_from_url_playwright_sync(
            zillow_url=url,
            headless=headless,
            proxy_url=None,
            slow_mo=3000,
            manual_mode=manual_mode,  # Пауза для капчи только для первой части
            wait_for_manual=manual_mode,
        )
        
        map_results = results.get("mapResults", [])
        total_count = results.get("totalResultCount", len(map_results))
        
        logger.info(f"[SEARCH] Часть {part_number}: получено {len(map_results)} домов (totalResultCount={total_count})")
        
        # Удаляем дубликаты
        unique_results = remove_duplicates(map_results)
        logger.info(f"[SEARCH] Часть {part_number}: {len(unique_results)} уникальных домов")
        
        return unique_results
        
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при парсинге части {part_number}: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def main():
    # Список URL для Seattle (4 части)
    seattle_urls = [
        {
            "name": "Часть 1",
            "url": "https://www.zillow.com/seattle-wa/sold/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22north%22%3A47.61739417897833%2C%22south%22%3A47.479746177237516%2C%22east%22%3A-122.21624062141869%2C%22west%22%3A-122.486092305989%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22rs%22%3A%7B%22value%22%3Atrue%7D%2C%22basu%22%3A%7B%22value%22%3Atrue%7D%2C%22hbas%22%3A%7B%22value%22%3Atrue%7D%2C%22price%22%3A%7B%22min%22%3A550000%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22mf%22%3A%7B%22value%22%3Afalse%7D%2C%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%2C%22apco%22%3A%7B%22value%22%3Afalse%7D%2C%22doz%22%3A%7B%22value%22%3A%2236m%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A12%2C%22usersSearchTerm%22%3A%22seattle%20west%22%2C%22listPriceActive%22%3Atrue%2C%22category%22%3A%22cat1%22%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A16037%2C%22regionType%22%3A6%7D%5D%7D"
        },
        {
            "name": "Часть 2",
            "url": "https://www.zillow.com/seattle-wa/sold/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22north%22%3A47.68511803781779%2C%22south%22%3A47.616428309056246%2C%22east%22%3A-122.31906578621361%2C%22west%22%3A-122.45399162849877%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22rs%22%3A%7B%22value%22%3Atrue%7D%2C%22basu%22%3A%7B%22value%22%3Atrue%7D%2C%22hbas%22%3A%7B%22value%22%3Atrue%7D%2C%22price%22%3A%7B%22min%22%3A550000%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22mf%22%3A%7B%22value%22%3Afalse%7D%2C%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%2C%22apco%22%3A%7B%22value%22%3Afalse%7D%2C%22doz%22%3A%7B%22value%22%3A%2236m%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A13%2C%22usersSearchTerm%22%3A%22seattle%20west%22%2C%22listPriceActive%22%3Atrue%2C%22category%22%3A%22cat1%22%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A16037%2C%22regionType%22%3A6%7D%5D%7D"
        },
        {
            "name": "Часть 3",
            "url": "https://www.zillow.com/seattle-wa/sold/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22north%22%3A47.69251356013621%2C%22south%22%3A47.62383356538589%2C%22east%22%3A-122.23735497078393%2C%22west%22%3A-122.37228081306908%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22rs%22%3A%7B%22value%22%3Atrue%7D%2C%22basu%22%3A%7B%22value%22%3Atrue%7D%2C%22hbas%22%3A%7B%22value%22%3Atrue%7D%2C%22price%22%3A%7B%22min%22%3A550000%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22mf%22%3A%7B%22value%22%3Afalse%7D%2C%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%2C%22apco%22%3A%7B%22value%22%3Afalse%7D%2C%22doz%22%3A%7B%22value%22%3A%2236m%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A13%2C%22usersSearchTerm%22%3A%22seattle%20west%22%2C%22listPriceActive%22%3Atrue%2C%22category%22%3A%22cat1%22%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A16037%2C%22regionType%22%3A6%7D%5D%7D"
        },
        {
            "name": "Часть 4",
            "url": "https://www.zillow.com/seattle-wa/sold/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22north%22%3A47.748884151696046%2C%22south%22%3A47.68027838977018%2C%22east%22%3A-122.26328649359526%2C%22west%22%3A-122.39821233588042%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22rs%22%3A%7B%22value%22%3Atrue%7D%2C%22basu%22%3A%7B%22value%22%3Atrue%7D%2C%22hbas%22%3A%7B%22value%22%3Atrue%7D%2C%22price%22%3A%7B%22min%22%3A550000%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22mf%22%3A%7B%22value%22%3Afalse%7D%2C%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%2C%22apco%22%3A%7B%22value%22%3Afalse%7D%2C%22doz%22%3A%7B%22value%22%3A%2236m%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A13%2C%22usersSearchTerm%22%3A%22seattle%20west%22%2C%22listPriceActive%22%3Atrue%2C%22category%22%3A%22cat1%22%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A16037%2C%22regionType%22%3A6%7D%5D%7D"
        },
    ]
    
    print("=" * 80)
    print("ПАРСИНГ SEATTLE ПО ГОТОВЫМ URL")
    print("=" * 80)
    print(f"\nВсего частей: {len(seattle_urls)}")
    for i, part in enumerate(seattle_urls, 1):
        print(f"  {i}. {part['name']}")
    
    print("\n" + "=" * 80)
    input("Нажмите Enter, чтобы начать парсинг...")
    
    # Парсим каждую часть
    all_results = []
    start_time = datetime.now()
    
    for i, part in enumerate(seattle_urls, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"ОБРАБОТКА {part['name']} ({i}/{len(seattle_urls)})")
        logger.info(f"{'=' * 80}")
        
        # Для первой части - пауза для капчи, для остальных - без паузы
        is_first_part = (i == 1)
        
        part_results = parse_url(
            url=part["url"],
            part_number=i,
            total_parts=len(seattle_urls),
            headless=False,  # Браузер виден для капчи
            manual_mode=is_first_part,  # Пауза только для первой части
        )
        
        all_results.extend(part_results)
        logger.info(f"[PROGRESS] {part['name']} завершена: {len(part_results)} домов")
        logger.info(f"[PROGRESS] Всего собрано: {len(all_results)} домов")
    
    # Удаляем дубликаты
    logger.info("\n" + "=" * 80)
    logger.info("УДАЛЕНИЕ ДУБЛИКАТОВ")
    logger.info("=" * 80)
    
    unique_results = remove_duplicates(all_results)
    logger.info(f"Всего собрано: {len(all_results)} домов")
    logger.info(f"После удаления дубликатов: {len(unique_results)} уникальных домов")
    
    # Сохраняем результаты
    output_file = "seattle_urls_results.json"
    output_data = {
        "metadata": {
            "parsed_at": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "total_parts": len(seattle_urls),
            "total_homes": len(unique_results),
            "homes_before_dedup": len(all_results),
        },
        "homes": unique_results,
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n{'=' * 80}")
    logger.info("ПАРСИНГ ЗАВЕРШЕН")
    logger.info(f"{'=' * 80}")
    logger.info(f"Результаты сохранены: {output_file}")
    logger.info(f"Логи сохранены: {log_file}")
    logger.info(f"Время выполнения: {(datetime.now() - start_time).total_seconds():.1f} секунд")
    logger.info(f"Найдено уникальных домов: {len(unique_results)}")
    
    print(f"\n[SUCCESS] Найдено {len(unique_results)} уникальных домов в Seattle")
    print(f"Результаты сохранены в: {output_file}")


if __name__ == "__main__":
    main()
