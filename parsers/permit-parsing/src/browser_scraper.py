"""
Playwright scraper для верификации Owner-Builder статуса на портале Accela
"""
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from loguru import logger

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright_stealth import stealth_async
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright playwright-stealth")

import sys
sys.path.append('..')
from config import ACCELA_BASE_URL, ACCELA_PERMIT_URL, BROWSER_CONFIG, PROXY_CONFIG


@dataclass
class VerificationResult:
    """Результат верификации пермита"""
    permit_num: str
    is_owner_builder: bool
    work_performer: Optional[str] = None
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    error: Optional[str] = None


class AccelaScraper:
    """
    Скрапер для портала Seattle Services (Accela)
    Проверяет секцию Contractor Disclosure
    """
    
    def __init__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is required. Install with: pip install playwright playwright-stealth")
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def init_browser(self) -> None:
        """Инициализация браузера с stealth режимом"""
        playwright = await async_playwright().start()
        
        launch_options = {
            "headless": BROWSER_CONFIG["headless"],
        }
        
        # Настройка прокси если указан
        if PROXY_CONFIG["url"]:
            launch_options["proxy"] = {
                "server": PROXY_CONFIG["url"],
                "username": PROXY_CONFIG.get("username"),
                "password": PROXY_CONFIG.get("password"),
            }
        
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # Создание контекста с реалистичными настройками
        self.context = await self.browser.new_context(
            viewport=BROWSER_CONFIG["viewport"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        
        logger.info("Browser initialized with stealth mode")
    
    async def close(self) -> None:
        """Закрытие браузера"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")
    
    async def verify_permit(self, permit_num: str) -> VerificationResult:
        """
        Верификация одного пермита
        
        Args:
            permit_num: Номер пермита (например, "6874081-CN")
            
        Returns:
            VerificationResult с информацией о владельце
        """
        if not self.context:
            await self.init_browser()
        
        page = await self.context.new_page()
        
        # Применяем stealth
        await stealth_async(page)
        
        try:
            # Формируем URL для страницы пермита
            permit_url = f"{ACCELA_BASE_URL}/portal/cap/capDetail.aspx?Module=DPD&TabName=DPD&capID1=&capID2=&capID3=&agencyCode=SEATTLE&IsToShowInspection=&permitNumber={permit_num}"
            
            logger.info(f"Navigating to permit {permit_num}")
            
            # Переход на страницу
            await page.goto(permit_url, timeout=BROWSER_CONFIG["timeout_ms"])
            
            # Ждем загрузки контента
            await page.wait_for_load_state("networkidle", timeout=BROWSER_CONFIG["timeout_ms"])
            
            # Задержка для имитации реального пользователя
            await asyncio.sleep(BROWSER_CONFIG["request_delay_ms"] / 1000)
            
            # Ищем секцию Contractor Disclosure
            result = await self._extract_contractor_disclosure(page, permit_num)
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying permit {permit_num}: {e}")
            return VerificationResult(
                permit_num=permit_num,
                is_owner_builder=False,
                error=str(e)
            )
        finally:
            await page.close()
    
    async def _extract_contractor_disclosure(self, page: Page, permit_num: str) -> VerificationResult:
        """
        Извлечение информации из секции Contractor Disclosure
        
        Ищем поле "Who will be performing all the work?"
        """
        try:
            # Селекторы для поиска информации (могут потребовать корректировки)
            selectors = {
                "work_performer": [
                    "text=Who will be performing all the work",
                    "[id*='ContractorDisclosure']",
                    ".contractor-disclosure",
                ],
                "owner_name": [
                    "[id*='ownerName']",
                    "[id*='OwnerName']",
                    "text=Owner Name",
                ],
                "owner_address": [
                    "[id*='ownerAddress']",
                    "[id*='OwnerAddress']",
                    "text=Owner Address",
                ],
            }
            
            work_performer = None
            owner_name = None
            owner_address = None
            
            # Пробуем найти информацию о том, кто выполняет работы
            for selector in selectors["work_performer"]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        # Получаем текст из соседнего элемента или родителя
                        parent = await element.evaluate_handle("el => el.parentElement")
                        work_performer = await parent.inner_text()
                        break
                except:
                    continue
            
            # Определяем, является ли owner-builder
            is_owner_builder = False
            if work_performer:
                work_performer_lower = work_performer.lower()
                if "owner" in work_performer_lower and "contractor" not in work_performer_lower:
                    is_owner_builder = True
                elif "licensed contractor" in work_performer_lower:
                    is_owner_builder = False
            
            # Извлекаем данные владельца если это owner-builder
            if is_owner_builder:
                for selector in selectors["owner_name"]:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            owner_name = await element.inner_text()
                            break
                    except:
                        continue
                
                for selector in selectors["owner_address"]:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            owner_address = await element.inner_text()
                            break
                    except:
                        continue
            
            return VerificationResult(
                permit_num=permit_num,
                is_owner_builder=is_owner_builder,
                work_performer=work_performer,
                owner_name=owner_name,
                owner_address=owner_address,
            )
            
        except Exception as e:
            logger.error(f"Error extracting contractor disclosure: {e}")
            return VerificationResult(
                permit_num=permit_num,
                is_owner_builder=False,
                error=str(e)
            )
    
    async def verify_batch(
        self,
        permit_nums: List[str],
        max_concurrent: int = 3
    ) -> List[VerificationResult]:
        """
        Пакетная верификация пермитов с ограничением параллельности
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_with_semaphore(permit_num: str) -> VerificationResult:
            async with semaphore:
                result = await self.verify_permit(permit_num)
                # Задержка между запросами
                await asyncio.sleep(BROWSER_CONFIG["request_delay_ms"] / 1000)
                return result
        
        tasks = [verify_with_semaphore(pn) for pn in permit_nums]
        results = await asyncio.gather(*tasks)
        
        return results


# Для тестирования
if __name__ == "__main__":
    async def test():
        scraper = AccelaScraper()
        await scraper.init_browser()
        
        # Тестовый пермит
        result = await scraper.verify_permit("6874081-CN")
        print(f"Result: {result}")
        
        await scraper.close()
    
    asyncio.run(test())
