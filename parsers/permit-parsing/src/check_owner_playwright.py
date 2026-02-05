"""
check_owner_playwright.py — Верификация Owner-Builder статуса через Accela Portal

Реализует проверку секции "Contractor Disclosure" согласно docs/master_spec.md раздел 5
"""
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright_stealth import stealth_async
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[WARN] Playwright not installed. Run: pip install playwright playwright-stealth")
    print("[WARN] Then: playwright install chromium")


# Конфигурация Accela Portal
ACCELA_BASE_URL = "https://cosaccela.seattle.gov"
ACCELA_PERMIT_URL = f"{ACCELA_BASE_URL}/portal/cap/capDetail.aspx"

# Настройки браузера
BROWSER_CONFIG = {
    "headless": True,
    "timeout_ms": 30000,
    "delay_between_requests_ms": 2000,
    "viewport": {"width": 1920, "height": 1080},
}


@dataclass
class VerificationResult:
    """
    Результат верификации одного пермита.
    
    Согласно master_spec.md раздел 5.3:
    - is_owner_builder = True: текст содержит "Owner" (без "Licensed Contractor")
    - is_owner_builder = False: текст содержит "Licensed Contractor"
    - is_owner_builder = None: неопределённо, требует ручной проверки
    """
    permitnum: str
    is_owner_builder: Optional[bool] = None
    work_performer_text: Optional[str] = None
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    verified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "permitnum": self.permitnum,
            "is_owner_builder": self.is_owner_builder,
            "work_performer_text": self.work_performer_text,
            "owner_name": self.owner_name,
            "owner_address": self.owner_address,
            "verified_at": self.verified_at,
            "error": self.error,
        }


def determine_owner_builder_status(text: str) -> Optional[bool]:
    """
    Определение статуса owner-builder по тексту.
    
    Логика согласно master_spec.md раздел 5.3:
    - Если содержит "Owner" (без "Licensed Contractor") -> True
    - Если содержит "Licensed Contractor" -> False
    - Иначе -> None (неопределённо)
    
    Args:
        text: Текст из поля "Who will be performing all the work?"
        
    Returns:
        True (owner-builder), False (contractor), None (неопределённо)
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Явный индикатор подрядчика
    if "licensed contractor" in text_lower:
        return False
    
    # Явные индикаторы owner-builder
    owner_keywords = ["owner", "property owner", "self", "homeowner"]
    for keyword in owner_keywords:
        if keyword in text_lower:
            return True
    
    # Неопределённо
    return None


class AccelaVerifier:
    """
    Верификатор статуса Owner-Builder через портал Accela.
    
    Использует Playwright для навигации и извлечения данных
    из секции Contractor Disclosure.
    """
    
    def __init__(self, headless: bool = True, proxy_config: Optional[Dict] = None):
        """
        Args:
            headless: Запуск браузера в headless режиме
            proxy_config: Настройки прокси {"url": ..., "username": ..., "password": ...}
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed.\n"
                "Install with: pip install playwright playwright-stealth\n"
                "Then run: playwright install chromium"
            )
        
        self.headless = headless
        self.proxy_config = proxy_config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._playwright = None
    
    async def __aenter__(self):
        await self.init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def init_browser(self) -> None:
        """Инициализация браузера с stealth режимом."""
        self._playwright = await async_playwright().start()
        
        launch_options = {"headless": self.headless}
        
        if self.proxy_config and self.proxy_config.get("url"):
            launch_options["proxy"] = {
                "server": self.proxy_config["url"],
                "username": self.proxy_config.get("username"),
                "password": self.proxy_config.get("password"),
            }
        
        self.browser = await self._playwright.chromium.launch(**launch_options)
        
        self.context = await self.browser.new_context(
            viewport=BROWSER_CONFIG["viewport"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        
        print("[BROWSER] Initialized with stealth mode")
    
    async def close(self) -> None:
        """Закрытие браузера."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[BROWSER] Closed")
    
    def _build_permit_url(self, permitnum: str) -> str:
        """Формирование URL страницы пермита."""
        return (
            f"{ACCELA_PERMIT_URL}?"
            f"Module=DPD&TabName=DPD&capID1=&capID2=&capID3="
            f"&agencyCode=SEATTLE&IsToShowInspection="
            f"&permitNumber={permitnum}"
        )
    
    async def verify_permit(self, permitnum: str) -> VerificationResult:
        """
        Верификация одного пермита.
        
        Args:
            permitnum: Номер пермита (например, "7111670-CN")
            
        Returns:
            VerificationResult с результатом проверки
        """
        if not self.context:
            await self.init_browser()
        
        page = await self.context.new_page()
        await stealth_async(page)
        
        try:
            url = self._build_permit_url(permitnum)
            print(f"[VERIFY] {permitnum} - navigating...")
            
            await page.goto(url, timeout=BROWSER_CONFIG["timeout_ms"])
            await page.wait_for_load_state("networkidle", timeout=BROWSER_CONFIG["timeout_ms"])
            
            # Задержка для имитации реального пользователя
            await asyncio.sleep(BROWSER_CONFIG["delay_between_requests_ms"] / 1000)
            
            # Извлечение данных из Contractor Disclosure
            result = await self._extract_contractor_disclosure(page, permitnum)
            
            return result
            
        except Exception as e:
            print(f"[VERIFY] {permitnum} - ERROR: {e}")
            return VerificationResult(
                permitnum=permitnum,
                is_owner_builder=None,
                error=str(e)
            )
        finally:
            await page.close()
    
    async def _extract_contractor_disclosure(
        self, 
        page: Page, 
        permitnum: str
    ) -> VerificationResult:
        """
        Извлечение данных из секции Contractor Disclosure.
        
        Ищет поле "Who will be performing all the work?"
        """
        work_performer_text = None
        owner_name = None
        
        # Селекторы для поиска (могут потребовать адаптации под реальную структуру)
        selectors_to_try = [
            # Текст вопроса
            "text=Who will be performing all the work",
            "text=who will be performing",
            # ID-based селекторы
            "[id*='ContractorDisclosure']",
            "[id*='WorkPerformer']",
            "[id*='OwnerBuilder']",
            # Class-based
            ".contractor-disclosure",
            ".work-performer",
        ]
        
        for selector in selectors_to_try:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Пробуем получить текст из родительского контейнера
                    parent = await element.evaluate_handle("el => el.closest('tr') || el.closest('div') || el.parentElement")
                    if parent:
                        work_performer_text = await parent.inner_text()
                        break
            except Exception:
                continue
        
        # Ищем имя владельца
        owner_selectors = [
            "[id*='OwnerName']",
            "[id*='ownerName']",
            "text=Owner Name",
        ]
        
        for selector in owner_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    owner_name = await element.inner_text()
                    break
            except Exception:
                continue
        
        # Определяем статус
        is_owner = determine_owner_builder_status(work_performer_text)
        
        status_str = {True: "OWNER", False: "CONTRACTOR", None: "UNKNOWN"}[is_owner]
        print(f"[VERIFY] {permitnum} - {status_str}")
        
        return VerificationResult(
            permitnum=permitnum,
            is_owner_builder=is_owner,
            work_performer_text=work_performer_text,
            owner_name=owner_name,
        )
    
    async def verify_batch(
        self,
        permit_numbers: List[str],
        max_concurrent: int = 3
    ) -> List[VerificationResult]:
        """
        Пакетная верификация с ограничением параллельности.
        
        Args:
            permit_numbers: Список номеров пермитов
            max_concurrent: Максимум параллельных проверок
            
        Returns:
            Список VerificationResult
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_with_limit(permitnum: str) -> VerificationResult:
            async with semaphore:
                result = await self.verify_permit(permitnum)
                await asyncio.sleep(BROWSER_CONFIG["delay_between_requests_ms"] / 1000)
                return result
        
        print(f"[BATCH] Verifying {len(permit_numbers)} permits (max {max_concurrent} concurrent)")
        
        tasks = [verify_with_limit(pn) for pn in permit_numbers]
        results = await asyncio.gather(*tasks)
        
        # Статистика
        owners = sum(1 for r in results if r.is_owner_builder is True)
        contractors = sum(1 for r in results if r.is_owner_builder is False)
        unknown = sum(1 for r in results if r.is_owner_builder is None)
        
        print(f"[BATCH] Results: {owners} owners, {contractors} contractors, {unknown} unknown")
        
        return results


# CLI интерфейс
async def main():
    """Пример использования."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python check_owner_playwright.py <permitnum> [permitnum2] ...")
        print("Example: python check_owner_playwright.py 7111670-CN 7103683-CN")
        return
    
    permit_numbers = sys.argv[1:]
    
    async with AccelaVerifier(headless=True) as verifier:
        results = await verifier.verify_batch(permit_numbers)
        
        print("\n" + "="*60)
        print("VERIFICATION RESULTS")
        print("="*60)
        
        for result in results:
            status = {True: "OWNER-BUILDER", False: "CONTRACTOR", None: "UNKNOWN"}[result.is_owner_builder]
            print(f"\n{result.permitnum}: {status}")
            if result.work_performer_text:
                print(f"  Text: {result.work_performer_text[:100]}...")
            if result.error:
                print(f"  Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
