# Основные функции для парсинга через Playwright (рекомендуется)
from core.playwright_search import (
    search_sold_playwright, 
    search_sold_playwright_sync, 
    ZillowPlaywrightScraper,
    search_from_url_playwright,
    search_from_url_playwright_sync,
    parse_zillow_url,
)
from core.tiling import (
    fetch_with_quadtree, 
    remove_duplicates, 
    divide_region,
    init_checkpoint,
    save_checkpoint,
    get_checkpoint_stats,
    is_tile_processed,
)

# Утилиты
from core.utils import parse_proxy

# Старые API функции (для обратной совместимости, но не рекомендуются из-за блокировок)
from core.search import for_sale, for_rent, sold
from core.details import get_from_home_id, get_from_deparment_id, get_from_deparment_url, get_from_home_url