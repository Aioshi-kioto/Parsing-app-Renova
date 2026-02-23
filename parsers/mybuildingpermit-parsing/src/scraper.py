"""
Playwright scraper для MyBuildingPermit
https://permitsearch.mybuildingpermit.com/

Использует Playwright из-за ASP.NET форм (ViewState) и Kendo UI Grid.
Поддерживает: поиск по датам, парсинг таблицы, CSV input (Export to Excel).
"""
import asyncio
import argparse
import csv
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright_stealth import Stealth
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    BASE_URL,
    SEARCH_URL,
    PERMIT_DETAILS_URL,
    JURISDICTIONS,
    JURISDICTION_VALUES,
    TARGET_CONFIG,
    FORM_ID,
    CONTENT_SELECTOR,
    BROWSER_CONFIG,
    TEST_MODE_LIMIT,
    TEST_CITIES,
)


def _safe_str(s: str) -> str:
    """ASCII-safe string for Windows console / Excel"""
    if s is None:
        return ""
    return str(s).encode("ascii", errors="replace").decode("ascii")


@dataclass
class PermitResult:
    """Результат парсинга пермита"""
    permit_number: str
    jurisdiction: str
    project_name: Optional[str] = None
    description: Optional[str] = None
    permit_type: Optional[str] = None
    permit_status: Optional[str] = None
    address: Optional[str] = None
    parcel: Optional[str] = None
    applied_date: Optional[str] = None
    issued_date: Optional[str] = None
    applicant_name: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_license: Optional[str] = None
    is_owner_builder: bool = False
    matches_target_type: bool = False  # подходит под TARGET_CONFIG.permit_types
    permit_url: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для экспорта"""
        return asdict(self)


class MyBuildingPermitScraper:
    """
    Скрапер для permitsearch.mybuildingpermit.com
    """

    def __init__(self, headless: Optional[bool] = None):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright required. Install: pip install playwright playwright-stealth && playwright install chromium"
            )
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._playwright = None
        # Если headless передан явно — используем его, иначе из BROWSER_CONFIG
        self._headless = headless if headless is not None else BROWSER_CONFIG["headless"]

    async def init_browser(self) -> None:
        """Инициализация браузера с stealth (playwright-stealth 2.x)"""
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self._headless,
        )
        self.context = await self.browser.new_context(
            viewport=BROWSER_CONFIG["viewport"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        try:
            await Stealth().apply_stealth_async(self.context)
        except Exception:
            pass  # fallback без stealth
        print("[Scraper] Browser started (headless=%s)" % self._headless)

    async def close(self) -> None:
        """Закрытие браузера"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def search_by_date_range(
        self,
        jurisdiction: str,
        date_from: str,
        date_to: str,
        limit: int = 100,
    ) -> List[PermitResult]:
        """
        Поиск пермитов по диапазону дат.
        
        Args:
            jurisdiction: Город/округ
            date_from: Дата начала (MM/DD/YYYY)
            date_to: Дата конца (MM/DD/YYYY)
            limit: Лимит результатов
        """
        if not self.context:
            await self.init_browser()

        page = await self.context.new_page()

        results: List[PermitResult] = []

        try:
            print(f"[{jurisdiction}] Opening site...")
            await page.goto(SEARCH_URL, timeout=BROWSER_CONFIG["timeout_ms"])
            await page.wait_for_load_state("networkidle", timeout=BROWSER_CONFIG["timeout_ms"])
            await asyncio.sleep(BROWSER_CONFIG["request_delay_ms"] / 1000)

            # Выбор Jurisdiction через Kendo dropdown
            print(f"[{jurisdiction}] Selecting jurisdiction...")
            jurisdiction_ok = await self._select_jurisdiction_kendo(page, jurisdiction)
            if not jurisdiction_ok:
                results.append(PermitResult(
                    permit_number="",
                    jurisdiction=jurisdiction,
                    error=f"Could not select jurisdiction: {jurisdiction}",
                ))
                return results
            
            await asyncio.sleep(1)

            # Permit # tab: требуется Permit Number (partial match). Используем год "26" для 2026.
            await page.fill("#txtPermitNumber", "26")
            await asyncio.sleep(0.3)
            
            # Date Type = Applied, From/To
            print(f"[{jurisdiction}] Setting date filter...")
            await self._select_date_type(page, "Applied")
            
            # Устанавливаем даты
            await self._set_date_range(page, date_from, date_to)
            
            await asyncio.sleep(0.5)

            # Submit — ждём активации кнопки после валидации формы
            print(f"[{jurisdiction}] Searching...")
            await page.wait_for_selector("#btnSearch:not([disabled])", timeout=10000)
            await page.click("#btnSearch")
            await page.wait_for_load_state("networkidle", timeout=BROWSER_CONFIG["timeout_ms"])
            await asyncio.sleep(2)
            
            # Проверяем на ошибку (>100 результатов)
            error_div = await page.query_selector("#searchError:not(.hidden)")
            if error_div:
                error_text = _safe_str(await error_div.inner_text())
                print(f"[{jurisdiction}] Error: {error_text}")
                results.append(PermitResult(
                    permit_number="",
                    jurisdiction=jurisdiction,
                    error=error_text,
                ))
                return results

            # Извлекаем все результаты (без фильтра по типам — парсим все пермиты для статистики и выгрузки)
            raw_results = await self._extract_results(page, jurisdiction, limit=500)
            filtered = self._filter_by_permit_types(raw_results, jurisdiction)
            results = raw_results[:limit]
            print(f"[{jurisdiction}] Found {len(raw_results)} raw, {len(filtered)} match target types, returning {len(results)} (all permits)")
            return results

        except Exception as e:
            err_msg = str(e).encode("ascii", errors="replace").decode("ascii")
            print(f"[{jurisdiction}] Error: {err_msg}")
            results.append(PermitResult(
                permit_number="",
                jurisdiction=jurisdiction,
                error=err_msg,
            ))
            return results
        finally:
            await page.close()

    async def _select_jurisdiction_kendo(self, page: Page, jurisdiction: str) -> bool:
        """Выбор jurisdiction через Kendo DropDownList API"""
        try:
            val = JURISDICTION_VALUES.get(jurisdiction)
            if val:
                await page.evaluate(
                    """([selId, val]) => {
                        const $ = window.jQuery;
                        if ($) {
                            const ddl = $("#" + selId).data("kendoDropDownList");
                            if (ddl) {
                                ddl.value(val);
                                ddl.trigger("change");
                            } else {
                                const sel = document.getElementById(selId);
                                if (sel) { sel.value = val; sel.dispatchEvent(new Event("change", {bubbles: true})); }
                            }
                        }
                    }""",
                    ["ddlJurisdictions", val],
                )
                await asyncio.sleep(1.5)
                return True
            # Fallback: ищем в option
            opts = await page.query_selector_all("#ddlJurisdictions option")
            for opt in opts:
                txt = await opt.inner_text()
                if jurisdiction in txt or txt.strip() == jurisdiction:
                    v = await opt.get_attribute("value")
                    if v:
                        await page.evaluate(
                            """([selId, val]) => {
                                const sel = document.getElementById(selId);
                                if (sel) { sel.value = val; sel.dispatchEvent(new Event("change", {bubbles: true})); }
                            }""",
                            ["ddlJurisdictions", v],
                        )
                        await asyncio.sleep(1.0)
                        return True
            return False
        except Exception as e:
            print(f"Error selecting jurisdiction: {e}")
            return False

    async def _select_date_type(self, page: Page, date_type: str) -> None:
        """Date Type (Applied, Issued, Finaled) — через Kendo MultiSelect API"""
        try:
            await page.evaluate(
                """([selId, val]) => {
                    const $ = window.jQuery;
                    if ($) {
                        const ms = $("#" + selId).data("kendoMultiSelect");
                        if (ms) ms.value([val]);
                    }
                }""",
                ["ddlDateRanges", date_type],
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error selecting date type: {e}")

    async def _set_date_range(self, page: Page, date_from: str, date_to: str) -> None:
        """From/To даты — Kendo DatePicker (readonly), через JS API"""
        try:
            await page.evaluate(
                """([fromId, toId, fromStr, toStr]) => {
                    const $ = window.jQuery;
                    if ($) {
                        const parts = (s) => s.split("/").map(Number);
                        const fromP = parts(fromStr);
                        const toP = parts(toStr);
                        const fromDate = new Date(fromP[2], fromP[0]-1, fromP[1]);
                        const toDate = new Date(toP[2], toP[0]-1, toP[1]);
                        $("#" + fromId).data("kendoDatePicker").value(fromDate);
                        $("#" + toId).data("kendoDatePicker").value(toDate);
                    }
                }""",
                ["FromDate", "ToDate", date_from, date_to],
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error setting date range: {e}")

    def _matches_target_type(self, jurisdiction: str, permit_type: Optional[str]) -> bool:
        """Проверка: permit_type подходит под TARGET_CONFIG для города"""
        if not permit_type or not permit_type.strip():
            return False
        cfg = TARGET_CONFIG.get(jurisdiction)
        if not cfg or not cfg.get("permit_types"):
            return False
        allowed = {t.strip().upper() for t in cfg["permit_types"]}
        return permit_type.strip().upper() in allowed

    def _filter_by_permit_types(
        self, results: List[PermitResult], jurisdiction: str
    ) -> List[PermitResult]:
        """Пост-фильтр по TARGET_CONFIG.permit_types для данного города"""
        cfg = TARGET_CONFIG.get(jurisdiction)
        if not cfg or not cfg.get("permit_types"):
            return results
        allowed = {t.strip().upper() for t in cfg["permit_types"]}
        filtered = []
        for r in results:
            if r.permit_type and r.permit_type.strip().upper() in allowed:
                filtered.append(r)
        return filtered

    async def _extract_results(self, page: Page, jurisdiction: str, limit: int = 100) -> List[PermitResult]:
        """Извлечение строк из Kendo Grid"""
        results: List[PermitResult] = []
        try:
            rows = await page.query_selector_all("#searchResultsGrid .k-master-row")
            
            for i, row in enumerate(rows):
                if i >= limit:
                    break
                    
                cells = await row.query_selector_all("td[role='gridcell']")
                
                if len(cells) >= 6:
                    # Permit # (с ссылкой)
                    permit_link = await cells[0].query_selector("a")
                    permit_number = _safe_str((await permit_link.inner_text()).strip() if permit_link else "")
                    permit_url = await permit_link.get_attribute("href") if permit_link else ""
                    
                    # Description (может содержать <br>)
                    description_html = await cells[1].inner_html()
                    description_parts = description_html.replace("<br>", "\n").split("\n")
                    project_name = _safe_str(description_parts[0].strip() if description_parts else "")
                    description = _safe_str(description_parts[1].strip() if len(description_parts) > 1 else "")
                    
                    # Address, Type, Status, Applied Date
                    address = _safe_str((await cells[2].inner_text()).strip())
                    permit_type = _safe_str((await cells[3].inner_text()).strip())
                    permit_status = _safe_str((await cells[4].inner_text()).strip())
                    applied_date = _safe_str((await cells[5].inner_text()).strip())
                    
                    results.append(PermitResult(
                        permit_number=permit_number,
                        jurisdiction=jurisdiction,
                        project_name=project_name,
                        description=description,
                        permit_type=permit_type,
                        permit_status=permit_status,
                        address=address,
                        applied_date=applied_date,
                        permit_url=f"{BASE_URL}{permit_url}" if permit_url and not permit_url.startswith("http") else permit_url,
                    ))
                    
        except Exception as e:
            print(f"Extract error: {e}")
            results.append(PermitResult(
                permit_number="",
                jurisdiction=jurisdiction,
                error=f"Extract error: {e}",
            ))
        return results

    async def get_permit_details(self, permit_number: str, city: str) -> PermitResult:
        """
        Получение деталей пермита по URL.
        URL: /PermitDetails/{PermitNumber}/{City}
        """
        if not self.context:
            await self.init_browser()

        page = await self.context.new_page()

        url = f"{PERMIT_DETAILS_URL}/{permit_number}/{city}"
        result = PermitResult(permit_number=permit_number, jurisdiction=city, permit_url=url)
        
        try:
            await page.goto(url, timeout=BROWSER_CONFIG["timeout_ms"])
            await page.wait_for_load_state("networkidle", timeout=BROWSER_CONFIG["timeout_ms"])
            await asyncio.sleep(BROWSER_CONFIG["request_delay_ms"] / 1000)

            # Получаем HTML и парсим BeautifulSoup
            content = await page.content()
            soup = BeautifulSoup(content, "lxml")
            
            # Извлекаем основные данные
            result.project_name = self._extract_table_value(soup, "Project Name:")
            result.permit_type = self._extract_table_value(soup, "Type:")
            result.address = self._extract_table_value(soup, "Address:")
            result.parcel = self._extract_table_value(soup, "Parcel:")
            result.permit_status = self._extract_table_value(soup, "Status:")
            result.applied_date = self._extract_table_value(soup, "Applied Date:")
            result.issued_date = self._extract_table_value(soup, "Issued Date:")
            
            # Извлекаем Description
            desc_div = soup.select_one(".panel-body p")
            if desc_div:
                result.description = desc_div.get_text(separator=" ").strip()
            
            # Извлекаем People
            people = await self._extract_people(page)
            for person in people:
                if person.get("type") == "Applicant":
                    result.applicant_name = person.get("name", "")
                elif person.get("type") == "Contractor":
                    result.contractor_name = person.get("name", "")
                    result.contractor_license = person.get("license", "")
            
            # Owner-builder: нет Contractor с непустым Contractor License Number
            result.is_owner_builder = self._is_owner_builder_from_people(people)
            # Подходит ли тип под TARGET_CONFIG для статистики
            result.matches_target_type = self._matches_target_type(city, result.permit_type)
            people_summary = ", ".join(f"{p.get('type')}(lic={bool(p.get('license'))})" for p in people[:5]) or "none"
            print(f"  [Details] {permit_number} People: {people_summary} -> owner_builder={result.is_owner_builder}, matches_type={result.matches_target_type}")
            
            return result
            
        except Exception as e:
            result.error = str(e)
            return result
        finally:
            await page.close()

    def _extract_table_value(self, soup: BeautifulSoup, label: str) -> Optional[str]:
        """Извлекает значение из таблицы по label"""
        th = soup.find("th", string=lambda t: t and label in t)
        if th:
            td = th.find_next_sibling("td")
            if td:
                return _safe_str(td.get_text(strip=True))
        return None

    def _is_owner_builder_from_people(self, people: List[Dict[str, str]]) -> bool:
        """
        Owner-builder: сохраняем только если НЕТ Contractor с непустым Contractor License Number.
        CONTRACTOR UNKNOWN с пустой лицензией → сохраняем.
        """
        for p in people:
            if (p.get("type") or "").strip().upper() == "CONTRACTOR":
                if (p.get("license") or "").strip():
                    return False
        return True

    async def _extract_people(self, page: Page) -> List[Dict[str, str]]:
        """Извлекает данные из таблицы People (#permitPeopleGrid)"""
        people = []
        try:
            rows = await page.query_selector_all("#permitPeopleGrid tbody tr")
            if not rows:
                rows = await page.query_selector_all("#permitPeopleGrid .k-grid-content tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) >= 3:
                    person_type = _safe_str((await cells[0].inner_text()).strip())
                    name = _safe_str((await cells[1].inner_text()).strip())
                    license_num = _safe_str((await cells[2].inner_text()).strip())
                    people.append({
                        "type": person_type,
                        "name": name,
                        "license": license_num,
                    })
        except Exception as e:
            print(f"Error extracting people: {e}")
        return people

    @staticmethod
    def _parse_csv_permit_codes(csv_path: str, jurisdiction: str) -> List[Tuple[str, str]]:
        """
        Читает CSV из Export to Excel (Kendo Grid: разделитель ;).
        Возвращает список (permit_number, jurisdiction).
        """
        path = Path(csv_path)
        if not path.exists():
            return []
        codes: List[Tuple[str, str]] = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = ";" if ";" in sample.split("\n")[0] else ","
            reader = csv.reader(f, delimiter=delimiter)
            for i, row in enumerate(reader):
                if not row:
                    continue
                code = (row[0] or "").strip()
                if code and (i > 0 or code != "Permit #") and not code.lower().startswith("permit #"):
                    codes.append((code, jurisdiction))
        return codes

    async def process_from_csv(
        self,
        csv_path: str,
        jurisdiction: str,
        owner_builder_only: bool = True,
        limit: Optional[int] = None,
    ) -> List[PermitResult]:
        """
        Обработка CSV из Export to Excel.
        Для каждого Permit # открывает PermitDetails, проверяет People.
        Если owner_builder_only: возвращает только пермиты без Contractor с лицензией.
        """
        codes = self._parse_csv_permit_codes(csv_path, jurisdiction)
        if not codes:
            print(f"No permit codes found in {csv_path}")
            return []
        if limit:
            codes = codes[:limit]
        print(f"Processing {len(codes)} permits from CSV (jurisdiction={jurisdiction})")
        await self.init_browser()
        results: List[PermitResult] = []
        try:
            for i, (code, jur) in enumerate(codes):
                print(f"  [{i+1}/{len(codes)}] {code}")
                detail = await self.get_permit_details(code, jur)
                if detail.error:
                    results.append(detail)
                    continue
                if owner_builder_only and not detail.is_owner_builder:
                    continue
                results.append(detail)
                await asyncio.sleep(BROWSER_CONFIG["request_delay_ms"] / 1000)
        finally:
            await self.close()
        return results

    async def search_with_adaptive_dates(
        self,
        jurisdiction: str,
        limit: int = 100,
        days_start: int = 7,
        days_min: int = 1,
    ) -> tuple[List[PermitResult], str, str]:
        """
        Поиск с адаптивным диапазоном: 7→6→5... дней пока не сработает.
        Возвращает (results, date_from_str, date_to_str).
        """
        date_to = datetime.now()
        for days in range(days_start, days_min - 1, -1):
            date_from = date_to - timedelta(days=days)
            date_from_str = date_from.strftime("%m/%d/%Y")
            date_to_str = date_to.strftime("%m/%d/%Y")
            print(f"[Scraper] [{jurisdiction}] Trying period {days} days: {date_from_str} — {date_to_str}")
            search_results = await self.search_by_date_range(
                jurisdiction=jurisdiction,
                date_from=date_from_str,
                date_to=date_to_str,
                limit=limit,
            )
            # Успех — нет ошибки "too many results"
            err = (search_results[0].error or "") if search_results else ""
            if not err or "too many" not in err.lower():
                print(f"[Scraper] [{jurisdiction}] Period OK: {len(search_results)} results")
                return (search_results, date_from_str, date_to_str)
            print(f"[Scraper] [{jurisdiction}] Too many results, reducing to {days - 1} days...")
        print(f"[Scraper] [{jurisdiction}] All date ranges failed (too many results)")
        return ([], date_from_str, date_to_str)

    def _deduplicate_results(self, results: List[PermitResult]) -> List[PermitResult]:
        """Убирает дубликаты по permit_number + jurisdiction"""
        seen: set = set()
        out: List[PermitResult] = []
        for r in results:
            key = (r.permit_number or "", r.jurisdiction or "")
            if key in seen or not key[0]:
                continue
            seen.add(key)
            out.append(r)
        return out

    async def run_with_adaptive_dates(
        self,
        cities: List[str],
        limit_per_city: int,
        progress_callback: Optional[Callable] = None,
    ) -> tuple[List[PermitResult], Dict[str, Any]]:
        """
        Полный парсинг с адаптивными датами, дедупликацией, статистикой.
        progress_callback(jurisdiction, date_from, date_to, analyzed, elapsed_sec, step=None, total_permits=None)
        """
        start_time = datetime.now()
        all_results: List[PermitResult] = []
        stats = {
            "date_from": None,
            "date_to": None,
            "jurisdictions_ok": {},
            "jurisdictions_failed": {},
        }
        print("[Scraper] ========== Starting browser ==========")
        await self.init_browser()
        try:
            for idx, city in enumerate(cities, 1):
                print(f"[Scraper] ---------- City {idx}/{len(cities)}: {city} ----------")
                try:
                    print(f"[Scraper] [{city}] Step 1/3: Searching permits (date range)...")
                    if progress_callback:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        progress_callback(city, "", "", len(all_results), elapsed, step=f"{city}: searching...", total_permits=None)
                    
                    search_results, df, dt = await self.search_with_adaptive_dates(
                        jurisdiction=city,
                        limit=limit_per_city,
                    )
                    
                    valid_search = [r for r in search_results if r.permit_number and not r.error]
                    total_raw = len(valid_search)
                    # Только по типам TARGET_CONFIG открываем PermitDetails и проверяем owner-builder
                    to_fetch = [r for r in valid_search if self._matches_target_type(city, r.permit_type)]
                    total_to_fetch = len(to_fetch)
                    print(f"[Scraper] [{city}] Search done. Total: {total_raw}, match TARGET types: {total_to_fetch}, skip details for {total_raw - total_to_fetch} (period: {df} - {dt})")
                    if search_results and search_results[0].error:
                        print(f"[Scraper] [{city}] Search error (e.g. too many results): {search_results[0].error}")
                    
                    stats["date_from"] = stats["date_from"] or df
                    stats["date_to"] = stats["date_to"] or dt
                    if progress_callback:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        planned = len(all_results) + total_raw
                        progress_callback(city, df, dt, len(all_results), elapsed, step=f"{city}: 0/{total_raw} permits", total_permits=planned if planned > 0 else None)
                    
                    if total_raw == 0:
                        print(f"[Scraper] [{city}] No permits, skipping.")
                        stats["jurisdictions_ok"][city] = 0
                        continue
                    
                    planned_total = len(all_results) + total_raw
                    # Не подходящие по типам — сохраняем только данные из грида, без открытия details
                    for r in valid_search:
                        if not self._matches_target_type(city, r.permit_type):
                            permit_url = f"{PERMIT_DETAILS_URL}/{r.permit_number}/{city}" if r.permit_number else None
                            grid_only = PermitResult(
                                permit_number=r.permit_number,
                                jurisdiction=city,
                                project_name=r.project_name,
                                description=r.description,
                                permit_type=r.permit_type,
                                permit_status=r.permit_status,
                                address=r.address,
                                applied_date=r.applied_date,
                                permit_url=permit_url,
                                matches_target_type=False,
                                is_owner_builder=False,
                            )
                            all_results.append(grid_only)
                    
                    # Подходящие по типам — открываем details и проверяем owner-builder (CONTRACTOR_FILTER)
                    print(f"[Scraper] [{city}] Step 2/3: Fetching details + owner-builder check for {total_to_fetch} permits (matching TARGET types)...")
                    for i, result in enumerate(to_fetch, 1):
                        permit_number = result.permit_number
                        print(f"[Scraper] [{city}] Permit {i}/{total_to_fetch}: {permit_number} (match type) — opening details...")
                        detailed = await self.get_permit_details(permit_number, city)
                        detailed.matches_target_type = True
                        all_results.append(detailed)
                        ob = "owner-builder" if detailed.is_owner_builder else "contractor"
                        print(f"[Scraper] [{city}] Permit {i}/{total_to_fetch}: {permit_number} — {ob}" + (f" (error: {detailed.error})" if detailed.error else ""))
                        if progress_callback:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            progress_callback(
                                city, df, dt, len(all_results), elapsed,
                                step=f"{city}: {i}/{total_to_fetch} {permit_number} ({ob})",
                                total_permits=planned_total,
                            )
                        await asyncio.sleep(BROWSER_CONFIG["request_delay_ms"] / 1000)
                    
                    print(f"[Scraper] [{city}] Step 3/3: Done. Total: {total_raw}, fetched details: {total_to_fetch}.")
                    stats["jurisdictions_ok"][city] = total_raw
                except Exception as e:
                    print(f"[Scraper] ERROR processing {city}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    stats["jurisdictions_failed"][city] = str(e)
            all_results = self._deduplicate_results(all_results)
            stats["total_analyzed"] = len(all_results)
            stats["elapsed_seconds"] = (datetime.now() - start_time).total_seconds()
            stats["owner_builders"] = sum(1 for r in all_results if r.is_owner_builder)
        finally:
            await self.close()
        return all_results, stats

    async def run_test_mode(
        self,
        cities: List[str] = None,
        limit_per_city: int = None,
        days_back: int = 7,
    ) -> List[PermitResult]:
        """
        Тестовый режим: парсинг с адаптивными датами (7→6→5...)
        """
        cities = cities or TEST_CITIES
        limit = limit_per_city or TEST_MODE_LIMIT
        
        results, stats = await self.run_with_adaptive_dates(
            cities=cities,
            limit_per_city=limit,
        )
        print(f"=== Stats: {stats.get('total_analyzed', 0)} analyzed, {stats.get('owner_builders', 0)} owner-builder, {stats.get('elapsed_seconds', 0):.1f}s ===")
        return results


async def main():
    """Основная функция с CLI"""
    parser = argparse.ArgumentParser(description="MyBuildingPermit Scraper")
    parser.add_argument("--test-mode", action="store_true", help="Тестовый режим (ограниченные данные)")
    parser.add_argument("--csv", type=str, help="CSV из Export to Excel — обработать коды пермитов")
    parser.add_argument("--jurisdiction", type=str, default="Auburn", help="Jurisdiction для --csv (Auburn, Bellevue, ...)")
    parser.add_argument("--cities", type=str, help="Города через запятую (Auburn,Bellevue)")
    parser.add_argument("--limit", type=int, default=None, help="Лимит (на город для test-mode, для csv — кол-во пермитов; None = все)")
    parser.add_argument("--days", type=int, default=30, help="Период в днях")
    parser.add_argument("--output", type=str, help="Имя выходного Excel файла")
    parser.add_argument("--all", action="store_true", help="С --csv: не фильтровать по owner-builder")
    
    args = parser.parse_args()
    
    scraper = MyBuildingPermitScraper()
    
    try:
        cities = args.cities.split(",") if args.cities else None
        
        if args.csv:
            results = await scraper.process_from_csv(
                csv_path=args.csv,
                jurisdiction=args.jurisdiction,
                owner_builder_only=not args.all,
                limit=args.limit if args.limit else None,
            )
        else:
            results = await scraper.run_test_mode(
                cities=cities,
                limit_per_city=args.limit or TEST_MODE_LIMIT,
                days_back=args.days,
            )
        
        # Фильтруем ошибки и экспортируем
        valid_results = [r for r in results if not r.error]
        error_results = [r for r in results if r.error]
        
        if args.csv:
            print(f"\nOwner-builder (сохранено): {len([r for r in valid_results if r.is_owner_builder])}")
        
        print(f"\n=== Результаты ===")
        print(f"Успешно: {len(valid_results)}")
        print(f"Ошибок: {len(error_results)}")
        
        if valid_results:
            from src.export import export_to_excel
            data = [r.to_dict() for r in valid_results]
            output_file = args.output or f"permits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = export_to_excel(data, output_file)
            print(f"\nЭкспортировано в: {output_path}")
        
        owner_builders = [r for r in valid_results if r.is_owner_builder]
        print(f"\nOwner-Builder лидов: {len(owner_builders)}")
        for r in owner_builders[:5]:
            print(f"  - {r.permit_number} | {r.address} | {r.applicant_name}")
                
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
