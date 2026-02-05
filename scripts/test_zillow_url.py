#!/usr/bin/env python3
"""Тест парсинга Zillow по URL (без БД)"""
import sys
from pathlib import Path

# Пути как в zillow_parser
PARSERS_PATH = Path(__file__).parent.parent / "parsers" / "zillow-parsing"
sys.path.insert(0, str(PARSERS_PATH / "src"))

URL = "https://www.zillow.com/homes/recently_sold/?searchQueryState=%7B%22isMapVisible%22%3Atrue%2C%22mapBounds%22%3A%7B%22west%22%3A-122.50854184537742%2C%22east%22%3A-122.23869016080711%2C%22south%22%3A47.480896042396395%2C%22north%22%3A47.61067211204784%7D%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22rs%22%3A%7B%22value%22%3Atrue%7D%2C%22price%22%3A%7B%22min%22%3A550000%2C%22max%22%3Anull%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22mf%22%3A%7B%22value%22%3Afalse%7D%2C%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%2C%22apco%22%3A%7B%22value%22%3Afalse%7D%2C%22basu%22%3A%7B%22value%22%3Atrue%7D%2C%22doz%22%3A%7B%22value%22%3A%2236m%22%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A12%7D"

def main():
    print("=" * 60)
    print("Тест парсинга Zillow по URL")
    print("=" * 60)
    print(f"URL: {URL[:80]}...")
    print()

    from core.playwright_search import search_from_url_playwright_sync, parse_zillow_url
    from core.tiling import remove_duplicates

    # 1. Парсинг URL
    print("[1/2] Парсинг URL (координаты, фильтры)...")
    url_data = parse_zillow_url(URL)
    print(f"      Координаты: N={url_data.get('north')}, S={url_data.get('south')}, W={url_data.get('west')}, E={url_data.get('east')}")
    print(f"      Zoom: {url_data.get('zoom')}")
    print()

    # 2. Запрос через Playwright (откроется браузер, может потребоваться капча)
    print("[2/2] Запуск Playwright (headless=False, manual_mode=True)...")
    print("      Если Zillow покажет капчу — решите её в браузере и нажмите Enter в консоли.")
    print()
    results = search_from_url_playwright_sync(
        zillow_url=URL,
        headless=False,
        proxy_url=None,
        slow_mo=3000,
        manual_mode=True,
        wait_for_manual=True,
    )

    map_results = results.get("mapResults", [])
    total_count = results.get("totalResultCount", len(map_results))
    unique = remove_duplicates(map_results)

    print()
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ:")
    print(f"  mapResults: {len(map_results)}")
    print(f"  totalResultCount: {total_count}")
    print(f"  Уникальных домов: {len(unique)}")
    if unique:
        print(f"  Пример: {unique[0].get('address', 'N/A')} — ${unique[0].get('price', 'N/A')}")
    print("=" * 60)
    print("OK: Парсинг сработал!" if map_results else "ОШИБКА: Нет результатов")

if __name__ == "__main__":
    main()
