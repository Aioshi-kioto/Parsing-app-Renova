"""Модуль для парсинга Zillow через Playwright с перехватом сетевых запросов"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Response, Playwright

# Импортируем stealth для обхода анти-ботов
try:
    from playwright_stealth.stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    logging.warning("playwright-stealth не установлен, работаем без stealth режима")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ZillowPlaywrightScraper:
    """Класс для парсинга Zillow через Playwright"""
    
    def __init__(
        self, 
        headless: bool = True, 
        proxy_url: Optional[str] = None,
        slow_mo: int = 1000,  # Задержка между действиями (мс)
        manual_mode: bool = False,  # Режим с паузами для ручного вмешательства
        wait_for_manual: bool = False,  # Ожидание ручного вмешательства на каждом шаге
    ):
        self.headless = headless
        self.proxy_url = proxy_url
        self.slow_mo = slow_mo  # Медленные действия
        self.manual_mode = manual_mode  # Режим с паузами
        self.wait_for_manual = wait_for_manual  # Ожидание ручного вмешательства
        self.api_response_data = None
        self.captured_requests = []
        self.playwright: Optional[Playwright] = None
    
    
    async def setup_browser(self, playwright: Playwright):
        """Настраивает браузер и страницу с stealth режимом"""
        logger.info("[BROWSER] Запуск браузера Firefox...")
        
        browser_options = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,  # Медленные действия для имитации человека
        }
        
        if self.proxy_url:
            # Парсим прокси URL
            browser_options["proxy"] = {"server": self.proxy_url}
            logger.info(f"[BROWSER] Используется прокси: {self.proxy_url}")
        
        # Используем Firefox (менее детектируемый чем Chromium)
        browser = await playwright.firefox.launch(**browser_options)
        logger.info("[BROWSER] Запущен Firefox (менее детектируемый чем Chromium)")
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",  # Таймзона для Seattle
            # Дополнительные настройки для обхода детекции
            java_script_enabled=True,
            accept_downloads=False,
            has_touch=False,
            is_mobile=False,
            # Дополнительные заголовки для реалистичности
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        
        page = await context.new_page()
        
        # Применяем stealth режим для обхода анти-ботов (КРИТИЧНО!)
        if STEALTH_AVAILABLE:
            logger.info("[BROWSER] Применение stealth режима для обхода анти-ботов...")
            try:
                # Используем Stealth класс с async методом
                stealth_instance = Stealth()
                await stealth_instance.apply_stealth_async(page)
                logger.info("[BROWSER] Stealth режим активирован (apply_stealth_async)")
                
                # Дополнительная проверка: скрываем navigator.webdriver (на всякий случай)
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Дополнительные маскировки для Firefox
                    if (navigator.userAgent.includes('Firefox')) {
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                        });
                    }
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    // Скрываем признаки автоматизации
                    delete navigator.__proto__.webdriver;
                """)
                logger.info("[BROWSER] Дополнительные маскировки применены")
            except Exception as e:
                logger.error(f"[BROWSER] Ошибка при применении stealth: {e}")
                logger.warning("[BROWSER] Продолжаем без stealth (риск блокировки!)")
        else:
            logger.error("[BROWSER] ⚠️  КРИТИЧНО: Stealth режим недоступен!")
            logger.error("[BROWSER] Установите: pip install playwright-stealth")
            logger.error("[BROWSER] Без stealth Zillow будет блокировать запросы!")
        
        # Перехватываем ответы API через event listener
        async def handle_response(response: Response):
            url = response.url
            # Логируем все запросы к Zillow API
            if "zillow.com" in url and ("async" in url or "api" in url.lower() or "search" in url.lower()):
                logger.info(f"[NETWORK] Запрос: {url[:150]}... статус: {response.status}")
            
            if "async-create-search-page-state" in url:
                logger.info(f"[NETWORK] *** ПЕРЕХВАЧЕН API ЗАПРОС ***: {url}, статус: {response.status}")
                try:
                    if response.status == 200:
                        body = await response.body()
                        body_text = body.decode('utf-8')
                        self.api_response_data = json.loads(body_text)
                        logger.info(f"[NETWORK] Получен ответ API, размер: {len(body)} байт")
                        search_results = self.api_response_data.get("cat1", {}).get("searchResults", {})
                        map_results_count = len(search_results.get("mapResults", []))
                        total_count = search_results.get("totalResultCount", 0)
                        logger.info(f"[NETWORK] *** УСПЕХ *** Найдено mapResults: {map_results_count}, totalResultCount: {total_count}")
                    else:
                        logger.warning(f"[NETWORK] API запрос вернул статус {response.status}")
                except Exception as e:
                    logger.error(f"[NETWORK] Ошибка при парсинге ответа: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
        
        page.on("response", handle_response)
        
        logger.info("[BROWSER] Браузер готов")
        return browser, context, page
    
    async def simulate_human_behavior(self, page: Page):
        """Имитация человеческого поведения для обхода детекции"""
        try:
            # Случайные движения мыши
            import random
            for _ in range(2):
                x = random.randint(100, 500)
                y = random.randint(100, 500)
                await page.mouse.move(x, y)
                await page.wait_for_timeout(random.randint(500, 1500))
            
            # Небольшая прокрутка
            await page.evaluate("window.scrollBy(0, 200)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollBy(0, -100)")
            await page.wait_for_timeout(500)
        except Exception as e:
            logger.debug(f"[BEHAVIOR] Ошибка при имитации поведения: {e}")
    
    async def handle_captcha(self, page: Page):
        """Обработка капчи Zillow (Press & Hold)"""
        try:
            # Ищем капчу по тексту или селекторам
            captcha_selectors = [
                'text="Press & Hold"',
                'text="Press and Hold"',
                '[class*="captcha"]',
                '[id*="captcha"]',
                'button:has-text("Press")',
            ]
            
            captcha_found = False
            for selector in captcha_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        captcha_found = True
                        logger.warning("[CAPTCHA] Обнаружена капча! Ожидание ручного прохождения...")
                        logger.warning("[CAPTCHA] Пожалуйста, пройдите капчу в браузере (Press & Hold)")
                        logger.warning("[CAPTCHA] После прохождения капча должна исчезнуть")
                        
                        # Ждем исчезновения капчи (до 60 секунд)
                        for attempt in range(60):
                            await page.wait_for_timeout(1000)
                            element = await page.query_selector(selector)
                            if not element:
                                logger.info("[CAPTCHA] Капча пройдена!")
                                # Дополнительная пауза после прохождения капчи
                                await page.wait_for_timeout(5000)
                                break
                        else:
                            logger.warning("[CAPTCHA] Капча не исчезла за 60 секунд, продолжаем...")
                        break
                except:
                    continue
            
            if not captcha_found:
                logger.debug("[CAPTCHA] Капча не обнаружена, продолжаем")
        except Exception as e:
            logger.debug(f"[CAPTCHA] Ошибка при проверке капчи: {e}")
    
    async def wait_for_manual_intervention(self, message: str = ""):
        """Ожидание ручного вмешательства пользователя"""
        if self.wait_for_manual:
            try:
                logger.info(f"[MANUAL] ПАУЗА для ручного вмешательства: {message}")
                logger.info(f"[MANUAL] Нажмите Enter в консоли, когда будете готовы продолжить...")
                input()  # Ждем нажатия Enter
                logger.info("[MANUAL] Продолжаем работу...")
            except EOFError:
                # Если input() не доступен (неинтерактивный режим), просто пропускаем
                logger.warning("[MANUAL] Интерактивный режим недоступен, пропускаем паузу")
    
    async def build_search_url(
        self,
        north: float,
        south: float,
        west: float,
        east: float,
        zoom: int,
        filters: Dict[str, Any],
    ) -> str:
        """Строит URL для поиска на Zillow"""
        import copy
        import urllib.parse

        # Если передали исходный searchQueryState из пользовательского URL — используем его как базу.
        raw_sqs = filters.get("_raw_search_query_state")
        if isinstance(raw_sqs, dict) and raw_sqs:
            search_query_state = copy.deepcopy(raw_sqs)
            # Жёстко переопределяем bounds/zoom под текущий тайл QuadTree
            search_query_state["pagination"] = {}
            search_query_state["mapBounds"] = {
                "north": north,
                "south": south,
                "east": east,
                "west": west,
            }
            search_query_state["mapZoom"] = zoom
            search_query_state["isMapVisible"] = True
            search_query_state["isListVisible"] = True

            # Гарантируем наличие filterState
            if not isinstance(search_query_state.get("filterState"), dict):
                search_query_state["filterState"] = {}

            filter_state = search_query_state["filterState"]
        else:
            # Иначе — дефолтный filterState
            filter_state = {
                "sortSelection": {"value": "globalrelevanceex"},
                "isNewConstruction": {"value": False},
                "isForSaleForeclosure": {"value": False},
                "isForSaleByOwner": {"value": False},
                "isForSaleByAgent": {"value": False},
                "isForRent": {"value": False},
                "isComingSoon": {"value": False},
                "isAuction": {"value": False},
                "isAllHomes": {"value": True},
                "isRecentlySold": {"value": True},
            }
            # Создаем searchQueryState
            search_query_state = {
                "pagination": {},
                "mapBounds": {
                    "north": north,
                    "south": south,
                    "east": east,
                    "west": west,
                },
                "mapZoom": zoom,
                "isMapVisible": True,
                "isListVisible": True,
                "filterState": filter_state,
            }
        
        # Добавляем/переопределяем фильтры (минимальный набор), не ломая исходный filterState
        if filters.get("basement_unfinished"):
            filter_state["basement"] = {"value": ["unfinished"]}
        
        if filters.get("home_type_houses"):
            filter_state["homeType"] = {"value": ["HOUSE"]}
        
        if filters.get("sold_in_last_months"):
            filter_state["daysOnZillow"] = {"max": filters["sold_in_last_months"] * 30}
        
        if filters.get("min_price"):
            filter_state["price"] = {"min": filters["min_price"]}

        # Кодируем в URL
        query_string = urllib.parse.quote(json.dumps(search_query_state))
        url = f"https://www.zillow.com/homes/?searchQueryState={query_string}"
        
        logger.info(f"[URL] Построен URL для поиска (длина: {len(url)} символов)")
        return url
    
    async def search_with_playwright(
        self,
        north: float,
        south: float,
        west: float,
        east: float,
        zoom: int,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Выполняет поиск через Playwright"""
        browser = None
        try:
            # Используем async context manager для playwright
            async with async_playwright() as p:
                browser, context, page = await self.setup_browser(p)
                
                # Сначала заходим на главную страницу Zillow для установки cookies
                logger.info("[SEARCH] Переход на главную страницу Zillow...")
                
                # Проверяем, что stealth работает (navigator.webdriver должен быть undefined)
                webdriver_value = await page.evaluate("() => navigator.webdriver")
                if webdriver_value is not None:
                    logger.warning(f"[BROWSER] ⚠️  navigator.webdriver = {webdriver_value} (должен быть undefined!)")
                    logger.warning("[BROWSER] Stealth может работать некорректно!")
                else:
                    logger.info("[BROWSER] navigator.webdriver = undefined (stealth работает)")
                
                await page.goto("https://www.zillow.com/", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_load_state("load")
                logger.info("[SEARCH] Главная страница загружена, ожидание установки cookies...")
                
                # Имитация человеческого поведения: случайные движения мыши
                await self.simulate_human_behavior(page)
                
                # Пауза для ручного вмешательства (если нужно)
                await self.wait_for_manual_intervention("Проверьте главную страницу, закройте попапы/капчу если нужно")
                
                # Медленное ожидание для установки cookies
                await page.wait_for_timeout(10000)  # Увеличено до 10 секунд для установки cookies
                
                # Проверяем наличие капчи и ждем её прохождения
                await self.handle_captcha(page)
                
                # Закрываем попапы автоматически, если есть
                try:
                    skip_button = page.locator('button:has-text("Skip"), button:has-text("Skip this question"), button:has-text("Continue")')
                    if await skip_button.count() > 0:
                        await skip_button.first.click()
                        logger.info("[SEARCH] Закрыт попап автоматически")
                        await page.wait_for_timeout(2000)
                except:
                    pass
                
                # Строим URL и переходим напрямую
                search_url = await self.build_search_url(north, south, west, east, zoom, filters)
                
                logger.info(f"[SEARCH] Переход на страницу поиска...")
                logger.info(f"[SEARCH] Область: N={north:.4f}, S={south:.4f}, W={west:.4f}, E={east:.4f}")
                logger.info(f"[SEARCH] Zoom: {zoom}")
                
                # Переходим на страницу поиска
                logger.info(f"[SEARCH] URL: {search_url[:100]}...")
                await page.goto(search_url, wait_until="domcontentloaded", timeout=120000)
                logger.info("[SEARCH] Страница поиска загружена")
                
                # Имитация человеческого поведения перед проверкой капчи
                await self.simulate_human_behavior(page)
                
                # Проверяем и обрабатываем капчу
                await self.handle_captcha(page)
                
                # Пауза для ручного вмешательства (если нужно)
                await self.wait_for_manual_intervention("Проверьте страницу поиска, закройте капчу если появилась")
                
                # Ждем загрузки контента
                await page.wait_for_load_state("networkidle", timeout=60000)
                logger.info("[SEARCH] Сеть успокоилась")
                
                # Еще раз проверяем капчу после загрузки
                await self.handle_captcha(page)
                
                # Медленное ожидание для загрузки результатов (увеличено для обхода капчи)
                logger.info("[SEARCH] Ожидание загрузки результатов и API запросов...")
                logger.info(f"[SEARCH] Медленный режим: ожидание {self.slow_mo * 7 / 1000:.1f} секунд...")
                await page.wait_for_timeout(self.slow_mo * 7)  # Увеличено для обхода капчи
                
                # Прокручиваем страницу для активации lazy loading (медленно, как человек)
                logger.info("[SEARCH] Медленная прокрутка страницы для загрузки всех результатов...")
                # Прокручиваем постепенно, как человек
                scroll_steps = 5
                for i in range(scroll_steps):
                    scroll_position = (i + 1) * (1.0 / scroll_steps)
                    await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position})")
                    await page.wait_for_timeout(self.slow_mo)  # Медленная прокрутка
                await page.wait_for_timeout(self.slow_mo * 2)
                
                # Прокручиваем обратно вверх
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(self.slow_mo)
                
                # Пытаемся найти элемент с результатами
                try:
                    await page.wait_for_selector('[data-testid="property-card"], .ListItem, [class*="property"]', timeout=10000)
                    logger.info("[SEARCH] Найдены карточки недвижимости на странице")
                except:
                    logger.warning("[SEARCH] Карточки недвижимости не найдены, возможно результаты загружаются через API")
                
                # Ждем еще немного для завершения всех запросов
                logger.info("[SEARCH] Финальное ожидание завершения всех запросов...")
                await page.wait_for_timeout(self.slow_mo * 4)  # Увеличено для стабильности
                
                # Финальная проверка капчи перед извлечением данных
                await self.handle_captcha(page)
                
                # Пауза для ручного вмешательства перед извлечением данных
                await self.wait_for_manual_intervention("Проверьте результаты на странице перед извлечением данных")
                
                # Пытаемся извлечь данные из window объекта на странице
                logger.info("[SEARCH] Попытка извлечь данные из window объекта...")
                try:
                    page_data = await page.evaluate("""
                        () => {
                            // Ищем данные в window
                            if (window.mapResults) return {mapResults: window.mapResults, source: 'window.mapResults'};
                            if (window.searchResults) return {searchResults: window.searchResults, source: 'window.searchResults'};
                            if (window.__NEXT_DATA__) return {nextData: window.__NEXT_DATA__, source: 'window.__NEXT_DATA__'};
                            // Ищем в глобальных переменных
                            for (let key in window) {
                                if (key.includes('search') || key.includes('map') || key.includes('result')) {
                                    try {
                                        let val = window[key];
                                        if (val && typeof val === 'object' && (val.mapResults || val.searchResults)) {
                                            return {data: val, source: `window.${key}`};
                                        }
                                    } catch(e) {}
                                }
                            }
                            return null;
                        }
                    """)
                    if page_data:
                        logger.info(f"[SEARCH] Найдены данные в {page_data.get('source', 'unknown')}")
                except Exception as e:
                    logger.warning(f"[SEARCH] Не удалось извлечь данные из window: {e}")
                
                # Если перехватили API ответ, используем его
                if self.api_response_data:
                    logger.info("[SEARCH] Используем данные из перехваченного API запроса")
                    search_results = self.api_response_data.get("cat1", {}).get("searchResults", {})
                    return search_results
                else:
                    # Пытаемся извлечь данные из страницы
                    logger.warning("[SEARCH] API ответ не перехвачен, пытаемся извлечь данные из страницы")
                    result = await self.extract_data_from_page(page)
                    return result
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при поиске: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
        finally:
            if browser:
                await browser.close()
                logger.info("[BROWSER] Браузер закрыт")
    
    async def search_from_url(
        self,
        zillow_url: str,
    ) -> Dict[str, Any]:
        """Выполняет поиск по готовому URL (пользователь настроил фильтры вручную)
        
        Args:
            zillow_url: URL страницы поиска Zillow с настроенными фильтрами
        
        Returns:
            Словарь с результатами поиска (searchResults)
        """
        browser = None
        try:
            # Используем async context manager для playwright
            async with async_playwright() as p:
                browser, context, page = await self.setup_browser(p)
                
                # Проверяем, что stealth работает
                webdriver_value = await page.evaluate("() => navigator.webdriver")
                if webdriver_value is not None:
                    logger.warning(f"[BROWSER] ⚠️  navigator.webdriver = {webdriver_value} (должен быть undefined!)")
                else:
                    logger.info("[BROWSER] navigator.webdriver = undefined (stealth работает)")
                
                # Переходим на URL с настроенными фильтрами
                logger.info(f"[SEARCH] Переход на URL: {zillow_url[:100]}...")
                await page.goto(zillow_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_load_state("load")
                logger.info("[SEARCH] Страница загружена")
                
                # Имитация человеческого поведения
                await self.simulate_human_behavior(page)
                
                # Раньше здесь была ручная пауза для капчи (input()).
                # По требованию — полностью автоматический режим без ожиданий.
                await page.wait_for_timeout(1500)
                
                # Проверяем капчу еще раз
                await self.handle_captcha(page)
                
                # Перехватываем ответы API
                async def handle_response(response: Response):
                    url = response.url
                    if "async-create-search-page-state" in url:
                        logger.info(f"[NETWORK] *** ПЕРЕХВАЧЕН API ЗАПРОС ***: {url}, статус: {response.status}")
                        try:
                            if response.status == 200:
                                body = await response.body()
                                body_text = body.decode('utf-8')
                                self.api_response_data = json.loads(body_text)
                                logger.info(f"[NETWORK] Получен ответ API, размер: {len(body)} байт")
                                search_results = self.api_response_data.get("cat1", {}).get("searchResults", {})
                                map_results_count = len(search_results.get("mapResults", []))
                                total_count = search_results.get("totalResultCount", 0)
                                logger.info(f"[NETWORK] *** УСПЕХ *** Найдено mapResults: {map_results_count}, totalResultCount: {total_count}")
                        except Exception as e:
                            logger.error(f"[NETWORK] Ошибка при парсинге ответа: {type(e).__name__}: {str(e)}")
                
                page.on("response", handle_response)
                
                # Медленная прокрутка для загрузки всех результатов
                logger.info("[SEARCH] Медленная прокрутка страницы для загрузки результатов...")
                for i in range(5):
                    await page.evaluate(f"window.scrollBy(0, {500 * (i + 1)})")
                    await page.wait_for_timeout(self.slow_mo)  # Медленная прокрутка
                
                # Дополнительное ожидание для загрузки данных
                await page.wait_for_timeout(5000)  # 5 секунд
                
                # Если перехватили API ответ, используем его
                if self.api_response_data:
                    logger.info("[SEARCH] Используем данные из перехваченного API запроса")
                    search_results = self.api_response_data.get("cat1", {}).get("searchResults", {})
                    return search_results
                else:
                    # Пытаемся извлечь данные из страницы
                    logger.warning("[SEARCH] API ответ не перехвачен, пытаемся извлечь данные из страницы")
                    result = await self.extract_data_from_page(page)
                    return result
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при поиске по URL: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
        finally:
            if browser:
                await browser.close()
                logger.info("[BROWSER] Браузер закрыт")
    
    async def extract_data_from_page(self, page: Page) -> Dict[str, Any]:
        """Извлекает данные напрямую со страницы"""
        logger.info("[EXTRACT] Извлечение данных со страницы...")
        
        try:
            # Метод 1: Ищем данные в window.__NEXT_DATA__ или других глобальных переменных
            logger.info("[EXTRACT] Поиск данных в window объектах...")
            page_data = await page.evaluate("""
                () => {
                    // Проверяем различные места, где могут быть данные
                    if (window.__NEXT_DATA__) {
                        try {
                            let data = window.__NEXT_DATA__;
                            if (data.props && data.props.pageProps) {
                                return {source: '__NEXT_DATA__', data: data};
                            }
                        } catch(e) {}
                    }
                    
                    // Ищем в других глобальных переменных
                    let searchVars = ['searchResults', 'mapResults', 'propertyData', 'listingData'];
                    for (let varName of searchVars) {
                        if (window[varName]) {
                            return {source: `window.${varName}`, data: window[varName]};
                        }
                    }
                    
                    return null;
                }
            """)
            
            if page_data:
                logger.info(f"[EXTRACT] Найдены данные в {page_data.get('source')}")
                # Пытаемся извлечь searchResults из структуры
                data = page_data.get('data', {})
                # Ищем вложенные структуры
                def find_search_results(obj, path=""):
                    if isinstance(obj, dict):
                        if "mapResults" in obj or "searchResults" in obj:
                            return obj
                        for key, value in obj.items():
                            result = find_search_results(value, f"{path}.{key}")
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            result = find_search_results(item, f"{path}[{i}]")
                            if result:
                                return result
                    return None
                
                search_results = find_search_results(data)
                if search_results:
                    logger.info("[EXTRACT] Найдены searchResults в структуре данных")
                    return search_results
            
            # Метод 2: Парсим HTML и ищем JSON в скриптах
            logger.info("[EXTRACT] Поиск данных в script тегах...")
            scripts = await page.query_selector_all("script[type='application/json'], script")
            for i, script in enumerate(scripts):
                try:
                    content = await script.inner_text()
                    if not content or len(content) < 100:
                        continue
                    
                    # Ищем JSON с mapResults или searchResults
                    if "mapResults" in content or "searchResults" in content or "cat1" in content:
                        import re
                        # Пытаемся найти JSON объект
                        patterns = [
                            r'\{[^{}]*"mapResults"[^{}]*\}',
                            r'\{[^{}]*"searchResults"[^{}]*\}',
                            r'\{[^{}]*"cat1"[^{}]*\}',
                        ]
                        for pattern in patterns:
                            matches = re.finditer(pattern, content, re.DOTALL)
                            for match in matches:
                                try:
                                    data = json.loads(match.group())
                                    if "mapResults" in str(data) or "searchResults" in str(data):
                                        logger.info(f"[EXTRACT] Найдены данные в script #{i}")
                                        return data
                                except:
                                    pass
                except:
                    continue
            
            # Метод 3: Пытаемся получить данные через выполнение JavaScript на странице
            logger.info("[EXTRACT] Попытка получить данные через JavaScript...")
            try:
                # Zillow может хранить данные в React state или других местах
                js_data = await page.evaluate("""
                    () => {
                        // Ищем в различных местах
                        let results = {};
                        
                        // Проверяем React DevTools данные (если доступны)
                        if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
                            try {
                                let fiber = window.__REACT_DEVTOOLS_GLOBAL_HOOK__.getFiberRoots(1);
                                if (fiber && fiber.values) {
                                    for (let root of fiber.values()) {
                                        // Пытаемся найти данные в React дереве
                                        let node = root;
                                        while (node) {
                                            if (node.memoizedState) {
                                                let state = node.memoizedState;
                                                if (state && typeof state === 'object') {
                                                    if (state.mapResults || state.searchResults) {
                                                        results.reactState = state;
                                                        break;
                                                    }
                                                }
                                            }
                                            node = node.child || node.sibling;
                                        }
                                    }
                                }
                            } catch(e) {}
                        }
                        
                        // Ищем в localStorage/sessionStorage
                        try {
                            for (let i = 0; i < localStorage.length; i++) {
                                let key = localStorage.key(i);
                                if (key && (key.includes('search') || key.includes('map') || key.includes('result'))) {
                                    try {
                                        let value = JSON.parse(localStorage.getItem(key));
                                        if (value && (value.mapResults || value.searchResults)) {
                                            results.localStorage = {[key]: value};
                                        }
                                    } catch(e) {}
                                }
                            }
                        } catch(e) {}
                        
                        return Object.keys(results).length > 0 ? results : null;
                    }
                """)
                if js_data:
                    logger.info(f"[EXTRACT] Найдены данные через JavaScript: {list(js_data.keys())}")
                    # Извлекаем searchResults из найденных данных
                    for source, data in js_data.items():
                        if isinstance(data, dict):
                            if "mapResults" in data or "searchResults" in data:
                                return data
            except Exception as e:
                logger.warning(f"[EXTRACT] Ошибка при выполнении JavaScript: {e}")
            
            # Метод 4: Парсим карточки недвижимости напрямую из DOM
            logger.info("[EXTRACT] Попытка парсинга карточек из DOM...")
            try:
                property_cards = await page.query_selector_all('[data-testid="property-card"], .ListItem, [class*="property-card"], [class*="SearchResultListItem"], [data-zpid]')
                if property_cards:
                    logger.info(f"[EXTRACT] Найдено {len(property_cards)} карточек на странице")
                    # Пока возвращаем пустой результат, но можем парсить карточки
            except:
                pass
            
            logger.warning("[EXTRACT] Не удалось извлечь данные из страницы")
            logger.info("[EXTRACT] Попробуйте запустить с headless=False чтобы увидеть, что происходит на странице")
            return {}
        except Exception as e:
            logger.error(f"[EXTRACT] Ошибка при извлечении данных: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}


def parse_zillow_url(zillow_url: str) -> Dict[str, Any]:
    """Извлекает searchQueryState из URL Zillow
    
    Args:
        zillow_url: URL страницы поиска Zillow (например, https://www.zillow.com/homes/?searchQueryState=...)
    
    Returns:
        Словарь с извлеченными данными:
        {
            "north": float,
            "south": float,
            "west": float,
            "east": float,
            "zoom": int,
            "filter_state": dict,
            "search_query_state": dict (полный объект)
        }
    """
    import urllib.parse
    
    try:
        # Парсим URL
        parsed_url = urllib.parse.urlparse(zillow_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Извлекаем searchQueryState
        if "searchQueryState" not in query_params:
            raise ValueError("URL не содержит searchQueryState. Убедитесь, что вы скопировали URL со страницы поиска Zillow.")
        
        # Декодируем JSON из URL
        search_query_state_str = query_params["searchQueryState"][0]
        search_query_state = json.loads(urllib.parse.unquote(search_query_state_str))
        
        # Извлекаем координаты
        map_bounds = search_query_state.get("mapBounds", {})
        north = map_bounds.get("north")
        south = map_bounds.get("south")
        west = map_bounds.get("west")
        east = map_bounds.get("east")
        zoom = search_query_state.get("mapZoom", 11)
        
        # Извлекаем фильтры
        filter_state = search_query_state.get("filterState", {})
        
        logger.info(f"[URL] Извлечено из URL: N={north}, S={south}, W={west}, E={east}, Zoom={zoom}")
        logger.info(f"[URL] Фильтры: {list(filter_state.keys())}")
        
        return {
            "north": north,
            "south": south,
            "west": west,
            "east": east,
            "zoom": zoom,
            "filter_state": filter_state,
            "search_query_state": search_query_state,
        }
    except json.JSONDecodeError as e:
        raise ValueError(f"Не удалось распарсить JSON из URL: {e}")
    except Exception as e:
        raise ValueError(f"Ошибка при парсинге URL: {e}")


async def search_sold_playwright(
    north: float,
    south: float,
    west: float,
    east: float,
    zoom: int,
    filters: Dict[str, Any],
    headless: bool = True,
    proxy_url: Optional[str] = None,
    slow_mo: int = 1000,
    manual_mode: bool = False,
    wait_for_manual: bool = False,
) -> Dict[str, Any]:
    """Асинхронная функция для поиска через Playwright
    
    Args:
        slow_mo: Задержка между действиями в миллисекундах (1000 = 1 секунда)
        manual_mode: Режим с паузами для ручного вмешательства
        wait_for_manual: Ожидание нажатия Enter на каждом шаге
    """
    scraper = ZillowPlaywrightScraper(
        headless=headless, 
        proxy_url=proxy_url,
        slow_mo=slow_mo,
        manual_mode=manual_mode,
        wait_for_manual=wait_for_manual,
    )
    try:
        return await scraper.search_with_playwright(north, south, west, east, zoom, filters)
    finally:
        # Очистка
        scraper.playwright = None


def search_sold_playwright_sync(
    north: float,
    south: float,
    west: float,
    east: float,
    zoom: int,
    filters: Dict[str, Any],
    headless: bool = True,
    proxy_url: Optional[str] = None,
    slow_mo: int = 1000,
    manual_mode: bool = False,
    wait_for_manual: bool = False,
) -> Dict[str, Any]:
    """Синхронная обертка для search_sold_playwright
    
    Args:
        slow_mo: Задержка между действиями в миллисекундах (1000 = 1 секунда, рекомендуется 2000-3000)
        manual_mode: Режим с паузами для ручного вмешательства
        wait_for_manual: Ожидание нажатия Enter на каждом шаге (для прохождения капчи вручную)
    """
    # Windows: если вызываем из worker-thread, стандартный loop может не поддерживать subprocess -> Playwright падает.
    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    search_sold_playwright(
                        north, south, west, east, zoom, filters,
                        headless, proxy_url, slow_mo, manual_mode, wait_for_manual
                    )
                )
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        except Exception:
            pass

    return asyncio.run(
        search_sold_playwright(
            north, south, west, east, zoom, filters,
            headless, proxy_url, slow_mo, manual_mode, wait_for_manual
        )
    )


async def search_from_url_playwright(
    zillow_url: str,
    headless: bool = False,
    proxy_url: Optional[str] = None,
    slow_mo: int = 3000,
    manual_mode: bool = True,
    wait_for_manual: bool = True,
) -> Dict[str, Any]:
    """Асинхронная функция для поиска по готовому URL
    
    Args:
        zillow_url: URL страницы поиска Zillow с настроенными фильтрами
        headless: Запускать браузер в headless режиме (False = показывать браузер)
        proxy_url: URL прокси (опционально)
        slow_mo: Задержка между действиями в миллисекундах (3000 = 3 секунды, рекомендуется для без прокси)
        manual_mode: Режим с паузами для ручного вмешательства
        wait_for_manual: Ожидание нажатия Enter для прохождения капчи вручную
    """
    scraper = ZillowPlaywrightScraper(
        headless=headless,
        proxy_url=proxy_url,
        slow_mo=slow_mo,
        manual_mode=manual_mode,
        wait_for_manual=wait_for_manual,
    )
    scraper.playwright = None  # Будет установлен в async context manager
    try:
        return await scraper.search_from_url(zillow_url)
    finally:
        scraper.playwright = None


def search_from_url_playwright_sync(
    zillow_url: str,
    headless: bool = False,
    proxy_url: Optional[str] = None,
    slow_mo: int = 3000,
    manual_mode: bool = True,
    wait_for_manual: bool = True,
) -> Dict[str, Any]:
    """Синхронная обертка для search_from_url_playwright.

    ВАЖНО (Windows):
    - Этот код часто вызывается из рабочего потока (ThreadPoolExecutor) в backend.
    - На Windows в дополнительных потоках по умолчанию создаётся SelectorEventLoop,
      который не поддерживает subprocess_exec и ломает Playwright
      с ошибкой NotImplementedError при запуске браузера.
    - Здесь мы принудительно создаём совместимый event loop и запускаем корутину вручную.
    """
    # Для Windows: в worker-thread по умолчанию SelectorEventLoop -> subprocess не работает -> Playwright падает.
    # Поэтому принудительно используем Proactor policy и отдельный event loop.
    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    search_from_url_playwright(
                        zillow_url,
                        headless,
                        proxy_url,
                        slow_mo,
                        manual_mode,
                        wait_for_manual,
                    )
                )
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        except Exception:
            # Fallback: если что-то пошло не так, пробуем стандартный asyncio.run
            pass

    # Unix или fallback — стандартный путь
    return asyncio.run(
        search_from_url_playwright(
            zillow_url,
            headless,
            proxy_url,
            slow_mo,
            manual_mode,
            wait_for_manual,
        )
    )
