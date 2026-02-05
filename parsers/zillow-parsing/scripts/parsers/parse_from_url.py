import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для импортов
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

"""
Скрипт для парсинга Zillow по готовому URL (пользователь настраивает фильтры вручную)

Использование:
1. Откройте Zillow в обычном браузере (Chrome/Firefox)
2. Настройте все фильтры:
   - Listing Status: Sold
   - Price: Min $600,000
   - Home Type: Houses
   - Basement: Unfinished
   - Sold in last: 36 months
3. Настройте область на карте (zoom, границы)
4. Скопируйте URL из адресной строки
5. Запустите этот скрипт и вставьте URL
6. Когда откроется браузер - пройдите капчу вручную
7. Нажмите Enter в консоли
8. Скрипт начнет медленно парсить все дома с QuadTree разбиением
"""

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from core.playwright_search import search_from_url_playwright_sync, parse_zillow_url
from core.tiling import (
    fetch_with_quadtree, 
    remove_duplicates, 
    init_checkpoint,
    get_checkpoint_stats,
)

# Настройка логирования с файлом
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, f"parse_from_url_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M%S'
))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)


def parse_from_url(zillow_url: str, output_file: str = "results_from_url.json"):
    """
    Парсит Zillow по готовому URL с QuadTree разбиением
    
    Args:
        zillow_url: URL страницы поиска Zillow с настроенными фильтрами
        output_file: Файл для сохранения результатов
    """
    logger.info("=" * 80)
    logger.info("ПАРСИНГ ZILLOW ПО URL (С РУЧНЫМ ПРОХОЖДЕНИЕМ КАПЧИ)")
    logger.info("=" * 80)
    
    # Извлекаем параметры из URL
    try:
        url_data = parse_zillow_url(zillow_url)
        logger.info(f"[URL] Извлечено из URL:")
        logger.info(f"  Координаты: N={url_data['north']:.4f}, S={url_data['south']:.4f}, W={url_data['west']:.4f}, E={url_data['east']:.4f}")
        logger.info(f"  Zoom: {url_data['zoom']}")
        logger.info(f"  Фильтры: {list(url_data['filter_state'].keys())}")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при парсинге URL: {e}")
        return None
    
    # Инициализируем checkpoint
    checkpoint_file = "scraping_checkpoint_url.json"
    init_checkpoint(checkpoint_file)
    checkpoint_stats = get_checkpoint_stats()
    logger.info(f"[CHECKPOINT] Загружен checkpoint: обработано {checkpoint_stats['processed_tiles']} регионов, найдено {checkpoint_stats['found_zpids']} уникальных домов.")
    
    # Преобразуем filter_state в формат для tiling
    filters = {}
    filter_state = url_data['filter_state']
    
    # Извлекаем фильтры из filter_state
    if filter_state.get("basement", {}).get("value") == ["unfinished"]:
        filters["basement_unfinished"] = True
    
    if filter_state.get("homeType", {}).get("value") == ["HOUSE"]:
        filters["home_type_houses"] = True
    
    if "price" in filter_state and "min" in filter_state["price"]:
        filters["min_price"] = filter_state["price"]["min"]
    
    if "daysOnZillow" in filter_state and "max" in filter_state["daysOnZillow"]:
        filters["sold_in_last_months"] = filter_state["daysOnZillow"]["max"] // 30
    
    logger.info(f"[FILTERS] Преобразованные фильтры: {filters}")
    
    # Сначала делаем один запрос по URL для проверки и получения начальных данных
    logger.info("=" * 80)
    logger.info("ШАГ 1: ПЕРВЫЙ ЗАПРОС ПО URL (С РУЧНЫМ ПРОХОЖДЕНИЕМ КАПЧИ)")
    logger.info("=" * 80)
    logger.info("Сейчас откроется браузер. Пожалуйста:")
    logger.info("  1. Пройдите капчу Zillow (если появилась)")
    logger.info("  2. Убедитесь, что страница полностью загрузилась")
    logger.info("  3. Нажмите Enter в этой консоли")
    logger.info("=" * 80)
    
    try:
        initial_results = search_from_url_playwright_sync(
            zillow_url=zillow_url,
            headless=False,  # Показываем браузер для прохождения капчи
            proxy_url=None,  # Без прокси
            slow_mo=3000,  # Медленный режим: 3 секунды между действиями
            manual_mode=True,  # Режим с паузами
            wait_for_manual=True,  # Ожидание Enter для прохождения капчи
        )
        
        map_results = initial_results.get("mapResults", [])
        total_count = initial_results.get("totalResultCount", 0)
        
        logger.info(f"[INITIAL] Получено результатов: mapResults={len(map_results)}, totalResultCount={total_count}")
        
        if total_count == 0:
            logger.warning("[INITIAL] Не найдено результатов. Проверьте фильтры в URL.")
            return None
        
        # Если результатов меньше 500, просто сохраняем их
        if total_count < 500:
            logger.info(f"[INITIAL] Результатов меньше 500 ({total_count}), сохраняем без разбиения")
            unique_results = remove_duplicates(map_results)
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(unique_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[SUCCESS] Сохранено {len(unique_results)} уникальных домов в {output_file}")
            checkpoint_stats = get_checkpoint_stats()
            logger.info(f"[CHECKPOINT] Статистика: обработано {checkpoint_stats['processed_tiles']} областей, найдено {checkpoint_stats['found_zpids']} уникальных домов")
            return unique_results
        
        # Если результатов >= 500, используем QuadTree
        logger.info(f"[QUADTREE] Результатов >= 500 ({total_count}), используем QuadTree разбиение")
        logger.info("=" * 80)
        logger.info("ШАГ 2: QUADTREE РАЗБИЕНИЕ (МЕДЛЕННЫЙ РЕЖИМ БЕЗ ПРОКСИ)")
        logger.info("=" * 80)
        logger.info("Скрипт будет медленно обрабатывать каждую область.")
        logger.info("Капча может появляться периодически - проходите её вручную.")
        logger.info("=" * 80)
        
        # Используем QuadTree для разбиения области
        new_results = fetch_with_quadtree(
            north=url_data['north'],
            south=url_data['south'],
            west=url_data['west'],
            east=url_data['east'],
            zoom=url_data['zoom'],
            filters=filters,
            proxy_url=None,  # Без прокси
            max_depth=10,
            use_playwright=True,
            headless=False,  # Показываем браузер для прохождения капчи
            checkpoint_file=checkpoint_file,
        )
        
        # Получаем все результаты из checkpoint (они уже сохранены там)
        # Но нам нужно собрать их из всех обработанных областей
        # Для простоты, просто используем new_results
        unique_results = remove_duplicates(new_results)
        
        # Сохраняем результаты
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_results, f, indent=2, ensure_ascii=False)
        
        logger.info("=" * 80)
        logger.info("✅ ПАРСИНГ ЗАВЕРШЕН")
        logger.info("=" * 80)
        logger.info(f"Всего найдено уникальных домов: {len(unique_results)}")
        logger.info(f"Результаты сохранены в: {output_file}")
        logger.info(f"Логи сохранены в: {log_file}")
        checkpoint_stats = get_checkpoint_stats()
        logger.info(f"Статистика checkpoint: обработано {checkpoint_stats['processed_tiles']} областей, найдено {checkpoint_stats['found_zpids']} уникальных домов")
        logger.info("=" * 80)
        return unique_results
        
    except KeyboardInterrupt:
        logger.warning("\n[INTERRUPT] Парсинг прерван пользователем")
        checkpoint_stats = get_checkpoint_stats()
        logger.info(f"[CHECKPOINT] Прогресс сохранен в {checkpoint_file}")
        logger.info(f"[CHECKPOINT] Обработано {checkpoint_stats['processed_tiles']} областей, найдено {checkpoint_stats['found_zpids']} уникальных домов")
        return None
    except Exception as e:
        logger.critical(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {type(e).__name__}: {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
        checkpoint_stats = get_checkpoint_stats()
        logger.info(f"[CHECKPOINT] Прогресс сохранен в {checkpoint_file}")
        logger.info(f"[CHECKPOINT] Обработано {checkpoint_stats['processed_tiles']} областей, найдено {checkpoint_stats['found_zpids']} уникальных домов")
        return None


if __name__ == "__main__":
    print("=" * 80)
    print("ПАРСИНГ ZILLOW ПО URL (С РУЧНЫМ ПРОХОЖДЕНИЕМ КАПЧИ)")
    print("=" * 80)
    print("\nИнструкция:")
    print("1. Откройте Zillow в обычном браузере")
    print("2. Настройте все фильтры (Sold, Price, Basement, Home Type, etc.)")
    print("3. Настройте область на карте")
    print("4. Скопируйте URL из адресной строки")
    print("5. Вставьте URL ниже")
    print("=" * 80)
    
    zillow_url = input("\nВставьте URL страницы поиска Zillow: ").strip()
    
    if not zillow_url:
        print("❌ URL не может быть пустым!")
        exit(1)
    
    if "zillow.com" not in zillow_url:
        print("❌ Это не похоже на URL Zillow!")
        exit(1)
    
    print(f"\n✅ URL принят: {zillow_url[:100]}...")
    print("\nНачинаем парсинг...")
    
    results = parse_from_url(zillow_url)
    
    if results:
        print(f"\n✅ Успешно! Найдено {len(results)} уникальных домов")
    else:
        print("\n❌ Парсинг завершился с ошибкой. Проверьте логи.")
