# -*- coding: utf-8 -*-
"""
MyBuildingPermit — Playwright-скрапер (permitsearch.mybuildingpermit.com).

Сайт: ASP.NET + Kendo UI. Поиск по умолчанию (Permit #) требует номер; для выборки
по датам переключаемся на «Project Info» и задаём минимум одно поле (тип пермита)
+ диапазон дат Applied.

Ограничение портала: до ~100 записей на один запрос (см. грид).
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_URL = "https://permitsearch.mybuildingpermit.com/"


class TooManyResultsError(RuntimeError):
    """Сервер отклонил запрос: слишком много совпадений."""


# Имена как в UI / MBP_JURISDICTIONS → value из <select id="ddlJurisdictions">
JURISDICTION_IDS: Dict[str, str] = {
    "Auburn": "24",
    "Bellevue": "1",
    "Bothell": "2",
    "Burien": "11",
    "Edmonds": "23",
    "Federal Way": "25",
    "Issaquah": "3",
    "Kenmore": "4",
    "King County": "20",
    "Kirkland": "5",
    "Mercer Island": "6",
    "Mill Creek": "13",
    "Newcastle": "19",
    "Sammamish": "7",
    "Snoqualmie": "9",
}


def _parse_kendo_date(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        if val.startswith("/Date("):
            m = re.search(r"/Date\((-?\d+)", val)
            if m:
                ms = int(m.group(1))
                return datetime.utcfromtimestamp(ms / 1000.0).strftime("%Y-%m-%d")
        if len(val) >= 10 and val[4] == "-" and val[7] == "-":
            return val[:10]
    return str(val)[:32] if val else None


@dataclass
class MBPScrapeResult:
    permit_number: str
    jurisdiction: str
    description: Optional[str] = None
    permit_type: Optional[str] = None
    permit_status: Optional[str] = None
    address: Optional[str] = None
    applied_date: Optional[str] = None
    issued_date: Optional[str] = None
    project_name: Optional[str] = None
    parcel: Optional[str] = None
    applicant_name: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_license: Optional[str] = None
    is_owner_builder: bool = False
    matches_target_type: bool = False
    permit_url: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permit_number": self.permit_number,
            "jurisdiction": self.jurisdiction,
            "project_name": self.project_name,
            "description": self.description,
            "permit_type": self.permit_type,
            "permit_status": self.permit_status,
            "address": self.address,
            "parcel": self.parcel,
            "applied_date": self.applied_date,
            "issued_date": self.issued_date,
            "applicant_name": self.applicant_name,
            "contractor_name": self.contractor_name,
            "contractor_license": self.contractor_license,
            "is_owner_builder": self.is_owner_builder,
            "matches_target_type": self.matches_target_type,
            "permit_url": self.permit_url,
            "error": self.error,
        }


class MyBuildingPermitScraper:
    def __init__(self, headless: bool = True, proxy_url: Optional[str] = None):
        self.headless = headless
        self.proxy_url = proxy_url
        self._browser = None
        self._playwright = None

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.debug("MBP browser close: %s", e)
        finally:
            self._browser = None
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._playwright = None

    async def run_with_adaptive_dates(
        self,
        cities: List[str],
        limit_per_city: int,
        progress_callback: Callable[..., None],
        days_back: int = 7,
    ) -> Tuple[List[MBPScrapeResult], Dict[str, Any]]:
        """
        Для каждого города: сужаем окно дат при ошибке поиска (days_back → 1).
        """
        from playwright.async_api import async_playwright

        try:
            from utils.decodo_proxy import playwright_proxy_config
        except ImportError:
            from backend.utils.decodo_proxy import playwright_proxy_config

        try:
            from services.rules_engine import classify_lead
        except ImportError:
            from backend.services.rules_engine import classify_lead

        try:
            from services.permit_parser import determine_owner_builder_status
        except ImportError:
            from backend.services.permit_parser import determine_owner_builder_status

        t0 = time.perf_counter()
        all_results: List[MBPScrapeResult] = []
        effective_days = max(1, min(int(days_back or 7), 30))
        date_from_str: Optional[str] = None
        date_to_str: Optional[str] = None  # последнее окно (для stats)

        playwright = await async_playwright().start()
        browser = None
        context = None
        launch_kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        if self.proxy_url:
            launch_kwargs["proxy"] = playwright_proxy_config(self.proxy_url)

        try:
            browser = await playwright.chromium.launch(**launch_kwargs)
            self._browser = browser
            context = await browser.new_context(
                viewport={"width": 1400, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120000)
            # Нативный <select> скрыт Kendo — ждём инициализацию DropDownList
            await page.wait_for_function(
                """() => {
                    const el = document.querySelector("#ddlJurisdictions");
                    return !!(el && window.jQuery && jQuery(el).data("kendoDropDownList"));
                }""",
                timeout=90000,
            )

            for city in cities:
                juris_id = JURISDICTION_IDS.get(city)
                if not juris_id:
                    logger.warning("Unknown jurisdiction %r, skip", city)
                    continue

                city_results: List[MBPScrapeResult] = []
                seen_keys = set()
                day_end = date.today()
                floor = date.today() - timedelta(days=effective_days)
                last_err: Optional[str] = None

                await self._prepare_city_form(page, juris_id)

                while len(city_results) < limit_per_city and day_end >= floor:
                    day_start = day_end - timedelta(days=1)
                    if day_start < floor:
                        day_start = floor

                    async def run_chunk(d0: date, d1: date) -> List[Dict[str, Any]]:
                        return await self._run_search_with_dates(
                            page,
                            d0.strftime("%m/%d/%Y"),
                            d1.strftime("%m/%d/%Y"),
                        )

                    date_from_str = day_start.strftime("%m/%d/%Y")
                    date_to_str = day_end.strftime("%m/%d/%Y")
                    elapsed = time.perf_counter() - t0
                    progress_callback(
                        city,
                        date_from_str,
                        date_to_str,
                        len(all_results) + len(city_results),
                        elapsed,
                        step=f"{city} {date_from_str}–{date_to_str}",
                        total_permits=len(city_results),
                    )

                    rows: List[Dict[str, Any]] = []
                    try:
                        rows = await run_chunk(day_start, day_end)
                    except TooManyResultsError:
                        if day_start < day_end:
                            try:
                                rows = await run_chunk(day_end, day_end)
                            except TooManyResultsError as e2:
                                last_err = str(e2)
                                logger.warning("MBP %s too many results even 1d %s", city, date_to_str)
                        else:
                            last_err = "too many (1d)"
                    except Exception as e:
                        last_err = str(e)
                        logger.warning("MBP chunk %s: %s", city, e)

                    for raw in rows:
                        r = self._row_to_result(
                            raw, city, classify_lead, determine_owner_builder_status
                        )
                        if not r:
                            continue
                        key = (r.permit_number, r.jurisdiction)
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        city_results.append(r)
                        if len(city_results) >= limit_per_city:
                            break

                    day_end = day_start - timedelta(days=1)
                    await asyncio.sleep(0.3)

                all_results.extend(city_results)
                if last_err and not city_results:
                    logger.error("MBP failed for %s: %s", city, last_err)

        finally:
            if context:
                await context.close()
            if browser:
                await browser.close()
            self._browser = None
            await playwright.stop()

        stats = {
            "date_from": date_from_str,
            "date_to": date_to_str,
            "elapsed_seconds": time.perf_counter() - t0,
        }
        return all_results, stats

    async def _prepare_city_form(self, page, juris_id: str) -> None:
        """Один раз на город: юрисдикция, вкладка Project Info, первый тип пермита, Applied dates enabled."""
        await page.evaluate(
            """([id]) => {
                const w = $("#ddlJurisdictions").data("kendoDropDownList");
                if (!w) throw new Error("kendoDropDownList missing");
                w.value(String(id));
                w.trigger("change");
            }""",
            [juris_id],
        )
        await page.wait_for_selector("#btnSearch:not([disabled])", timeout=60000)
        await asyncio.sleep(0.8)

        await page.locator("label[for='radioProjectInfo']").click()
        await asyncio.sleep(0.25)
        await page.fill("#txtProjectName", "")

        ok_type = await page.evaluate(
            """() => {
                const ms = $("#ddlPermitTypes").data("kendoMultiSelect");
                if (!ms) return false;
                const data = ms.dataSource.data();
                if (!data || data.length === 0) return false;
                const first = data[0];
                const v = first.Value !== undefined ? first.Value : first.value;
                ms.value([v]);
                return true;
            }"""
        )
        if not ok_type:
            await page.fill("#txtProjectName", "roof")

        await page.evaluate(
            """() => {
                const ms = $("#ddlDateRanges").data("kendoMultiSelect");
                if (!ms) throw new Error("ddlDateRanges kendoMultiSelect missing");
                ms.value(["Applied"]);
                if (typeof toggleDateControls === "function") {
                    toggleDateControls.call(ms);
                } else {
                    ms.trigger("change");
                }
            }"""
        )
        await asyncio.sleep(0.25)

    async def _run_search_with_dates(
        self, page, date_from: str, date_to: str
    ) -> List[Dict[str, Any]]:
        """Повторный поиск при тех же фильтрах, меняются только даты."""
        await page.evaluate(
            """() => {
                $("#searchError").addClass("hidden");
                $("#gridContainer").addClass("hidden");
                $("#divWaitMessage").addClass("hidden");
            }"""
        )

        await page.evaluate(
            """([fromStr, toStr]) => {
                const kendo = window.kendo;
                if (!kendo) throw new Error("kendo missing");
                const fromP = $("#FromDate").data("kendoDatePicker");
                const toP = $("#ToDate").data("kendoDatePicker");
                if (!fromP || !toP) throw new Error("kendoDatePicker missing");
                fromP.value(kendo.parseDate(fromStr, "MM/dd/yyyy"));
                toP.value(kendo.parseDate(toStr, "MM/dd/yyyy"));
            }""",
            [date_from, date_to],
        )

        await page.locator("#btnSearch").click()

        await page.wait_for_function(
            """() => {
                const err = document.querySelector("#searchError");
                const grid = document.querySelector("#gridContainer");
                const errShown = err && !err.classList.contains("hidden");
                const gridShown = grid && !grid.classList.contains("hidden");
                return errShown || gridShown;
            }""",
            timeout=90000,
        )
        await asyncio.sleep(0.35)

        err_el = page.locator("#searchError")
        if await err_el.is_visible():
            txt = (await err_el.inner_text()).strip()
            low = txt.lower()
            if "too many" in low:
                raise TooManyResultsError(txt)
            raise RuntimeError(f"searchError visible: {txt}")

        grid_vis = page.locator("#gridContainer")
        await grid_vis.wait_for(state="visible", timeout=15000)

        data = await page.evaluate(
            """() => {
                const grid = $("#searchResultsGrid").data("kendoGrid");
                if (!grid) return [];
                const ds = grid.dataSource;
                if (!ds) return [];
                const rows = ds.data();
                if (!rows) return [];
                const out = [];
                for (let i = 0; i < rows.length; i++) {
                    const item = rows[i];
                    if (item && item.toJSON) out.push(item.toJSON());
                    else out.push(item);
                }
                return out;
            }"""
        )
        if not isinstance(data, list):
            return []
        return data

    def _row_to_result(
        self,
        raw: Dict[str, Any],
        city_name: str,
        classify_lead,
        determine_owner_builder_status,
    ) -> Optional[MBPScrapeResult]:
        pnum = raw.get("PermitNumber")
        if pnum is None:
            return None
        permit_number = str(pnum).strip()
        if not permit_number:
            return None

        juris = (raw.get("Jurisdiction") or city_name or "").strip()
        desc = (raw.get("PermitDescription") or "").strip() or None
        ptype = (raw.get("PermitType") or "").strip() or None
        pstat = (raw.get("PermitStatus") or "").strip() or None
        addr = (raw.get("Address") or "").strip() or None

        applied = _parse_kendo_date(raw.get("AppliedDate"))
        issued = _parse_kendo_date(raw.get("IssuedDate"))

        base_url = BASE_URL.rstrip("/")
        permit_url = f"{base_url}/PermitDetails/{permit_number}/{juris}"

        combo = " ".join(x for x in [ptype, desc, pstat] if x)
        ob_raw = determine_owner_builder_status(combo)
        ob = ob_raw is True

        record = {
            "address": addr,
            "city": juris,
            "permit_type": ptype,
            "description": desc,
            "applicant_name": None,
            "contractor_name": None,
            "applied_date": applied,
            "issued_date": issued,
            "permit_number": permit_number,
        }
        matches = classify_lead(record, "mybuildingpermit")
        mtt = any(m.case_type != "GENERAL" for m in matches)

        return MBPScrapeResult(
            permit_number=permit_number,
            jurisdiction=juris,
            project_name=desc,
            description=desc,
            permit_type=ptype,
            permit_status=pstat,
            address=addr,
            applied_date=applied,
            issued_date=issued,
            parcel=None,
            applicant_name=None,
            contractor_name=None,
            contractor_license=None,
            is_owner_builder=bool(ob),
            matches_target_type=mtt,
            permit_url=permit_url,
            error=None,
        )
