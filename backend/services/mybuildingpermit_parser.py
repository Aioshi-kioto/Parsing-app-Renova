"""
MyBuildingPermit Parser Service

Playwright-скрапер: backend/services/mbp_playwright_scraper.py (Kendo UI на permitsearch.mybuildingpermit.com).

Прокси Decodo: PROXY_URL в .env передаётся в браузер (см. docs/integrations/decodo/README.md).
"""
import asyncio
import os
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

from database import update_mbp_job, insert_mbp_permit, get_connection
from services.lead_pipeline import ingest_record_to_leads


def _run_async(coro):
    """Запуск async в новом event loop"""
    import sys
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def run_parse_job(
    job_id: int,
    jurisdictions: List[str],
    days_back: int = 7,
    limit_per_city: Optional[int] = None,
    headless: bool = False
) -> List[Dict]:
    """Основная функция парсинга с адаптивными датами и сохранением в БД"""
    from services.mbp_playwright_scraper import MyBuildingPermitScraper

    def check_cancelled():
        """Проверяет, была ли задача отменена"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM mbp_jobs WHERE id = ?", (job_id,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == "cancelled"

    def on_progress(jurisdiction: str, date_from: str, date_to: str, analyzed: int, elapsed: float, step: Optional[str] = None, total_permits: Optional[int] = None):
        # Проверяем, не была ли задача отменена
        if check_cancelled():
            print(f"[MBP] Job {job_id} was cancelled, stopping...")
            raise Exception("Job was cancelled by user")
        
        display = step or jurisdiction
        print(f"[MBP] Job {job_id} | {display} | analyzed: {analyzed}" + (f" | total: {total_permits}" if total_permits else "") + f" | {elapsed:.1f}s")
        kwargs = dict(
            job_id=job_id,
            status="running",
            current_jurisdiction=display,
            date_from_str=date_from,
            date_to_str=date_to,
            analyzed_count=analyzed,
            elapsed_seconds=round(elapsed, 1),
        )
        if total_permits is not None:
            kwargs["total_permits"] = total_permits
        update_mbp_job(**kwargs)

    # Проверка cancelled ПЕРЕД открытием браузера
    if check_cancelled():
        print(f"[MBP] Job {job_id} was cancelled before starting browser")
        update_mbp_job(
            job_id,
            status="cancelled",
            completed_at=datetime.now().isoformat(),
            current_jurisdiction=None,
        )
        return []
    
    # Используем большое значение если limit_per_city не указан
    effective_limit = limit_per_city if limit_per_city is not None else 9999
    print(f"\n[MBP] Job {job_id}: jurisdictions={jurisdictions}, limit={effective_limit}, headless={headless}")
    update_mbp_job(job_id, status="running")

    try:
        from services.outbound.telegram_bot import get_telegram_bot
        bot = get_telegram_bot()
        _run_async(bot.send_parser_start("MyBuildingPermit", {
            "Jurisdictions": ", ".join(jurisdictions),
            "Days Back": days_back,
            "Limit / City": effective_limit
        }))
    except Exception as e:
        print(f"[MBP] Failed to send Telegram start alert: {e}")

    scraper = None
    try:
        # Проверка cancelled перед созданием scraper
        if check_cancelled():
            print(f"[MBP] Job {job_id} was cancelled before creating scraper")
            update_mbp_job(
                job_id,
                status="cancelled",
                completed_at=datetime.now().isoformat(),
                current_jurisdiction=None,
            )
            return []
        
        proxy_url = (os.environ.get("PROXY_URL") or "").strip() or None
        if proxy_url:
            from utils.decodo_proxy import normalize_proxy_url_for_playwright

            proxy_url = normalize_proxy_url_for_playwright(proxy_url)
        try:
            if proxy_url:
                scraper = MyBuildingPermitScraper(headless=headless, proxy_url=proxy_url)
            else:
                scraper = MyBuildingPermitScraper(headless=headless)
        except TypeError:
            # Старый scraper без proxy_url — только headless
            scraper = MyBuildingPermitScraper(headless=headless)
        
        # Проверка cancelled перед запуском парсинга (браузер ещё не открыт)
        if check_cancelled():
            print(f"[MBP] Job {job_id} was cancelled before starting parse")
            update_mbp_job(
                job_id,
                status="cancelled",
                completed_at=datetime.now().isoformat(),
                current_jurisdiction=None,
            )
            return []
        
        results, stats = await scraper.run_with_adaptive_dates(
            cities=jurisdictions,
            limit_per_city=effective_limit,
            progress_callback=on_progress,
            days_back=days_back,
        )

        # Сохраняем в БД (insert_mbp_permit уже дедуплицирует по permit_number,jurisdiction)
        total_count = len(results)
        matching_count = sum(1 for r in results if r.matches_target_type)
        owner_count = sum(1 for r in results if r.is_owner_builder)
        print(f"[MBP] Job {job_id}: Saving {total_count} permits (total: {total_count}, matching types: {matching_count}, owner-builders: {owner_count})...")
        saved_count = 0
        for r in results:
            if r.permit_number and not r.error:
                row = r.to_dict()
                insert_mbp_permit(job_id, row)
                # Sprint 1: классифицируем MBP запись в leads (если подходит под кейсы Rules Engine)
                ingest_record_to_leads(
                    {
                        "address": row.get("address"),
                        "city": row.get("jurisdiction"),
                        "permit_type": row.get("permit_type"),
                        "description": row.get("description"),
                        "applicant_name": row.get("applicant_name"),
                        "contractor_name": row.get("contractor_name"),
                        "applied_date": row.get("applied_date"),
                        "issued_date": row.get("issued_date"),
                    },
                    source="mybuildingpermit",
                )
                saved_count += 1
                if r.is_owner_builder:
                    print(f"[MBP] Job {job_id}: Saved owner-builder {r.permit_number} ({r.jurisdiction})")
        print(f"[MBP] Job {job_id}: Saved {saved_count} permits to database")
        print(f"[MBP] Job {job_id}: Found {owner_count} owner-builder permits")

        update_mbp_job(
            job_id,
            status="completed",
            total_permits=len(results),
            analyzed_count=len(results),
            owner_builders_found=owner_count,
            date_from_str=stats.get("date_from"),
            date_to_str=stats.get("date_to"),
            elapsed_seconds=stats.get("elapsed_seconds"),
            current_jurisdiction=None,
            completed_at=datetime.now().isoformat(),
        )

        print(f"[MBP] Job {job_id} completed: total={total_count}, matching_types={matching_count}, owner_builders={owner_count}, {stats.get('elapsed_seconds', 0):.1f}s")
        
        try:
            from services.outbound.telegram_bot import get_telegram_bot
            bot = get_telegram_bot()
            _run_async(bot.send_parser_finish("MyBuildingPermit", {
                "Total Parsed": total_count,
                "Matching Types": matching_count,
                "Owner Builders": owner_count,
                "Elapsed Time": f"{stats.get('elapsed_seconds', 0):.1f}s"
            }))
        except Exception as alert_err:
            print(f"[MBP] Failed to send Telegram finish alert: {alert_err}")

        return [r.to_dict() for r in results]

    except Exception as e:
        import traceback
        err_msg = str(e)
        
        # Закрываем браузер при любой ошибке или отмене
        if scraper:
            try:
                await scraper.close()
                print(f"[MBP] Job {job_id}: Browser closed")
            except Exception as close_err:
                print(f"[MBP] Job {job_id}: Error closing browser: {close_err}")
        
        if "cancelled" in err_msg.lower():
            print(f"[MBP] Job {job_id} CANCELLED")
            update_mbp_job(
                job_id,
                status="cancelled",
                completed_at=datetime.now().isoformat(),
                current_jurisdiction=None,
            )
        else:
            print(f"[MBP] Job {job_id} FAILED: {err_msg}")
            traceback.print_exc()
            update_mbp_job(
                job_id,
                status="failed",
                error_message=err_msg,
                completed_at=datetime.now().isoformat(),
            )
            try:
                from services.outbound.telegram_bot import get_telegram_bot
                bot = get_telegram_bot()
                _run_async(bot.send_error_alert("MBP Parser", err_msg))
            except Exception as alert_err:
                print(f"[MBP] Failed to send Telegram alert: {alert_err}")
        raise


def start_mbp_parse_job(
    job_id: int,
    jurisdictions: List[str],
    days_back: int = 7,
    limit_per_city: Optional[int] = None,
    headless: bool = False
):
    """Запуск парсинга в фоновом потоке"""
    def run():
        try:
            _run_async(run_parse_job(job_id, jurisdictions, days_back, limit_per_city, headless))
        except Exception as e:
            import traceback
            err_msg = str(e)
            print(f"[MBP] Job {job_id} FAILED (thread): {err_msg}")
            traceback.print_exc()
            update_mbp_job(
                job_id,
                status="failed",
                error_message=err_msg,
                completed_at=datetime.now().isoformat(),
                current_jurisdiction=None,
            )
            try:
                from services.outbound.telegram_bot import get_telegram_bot
                bot = get_telegram_bot()
                _run_async(bot.send_error_alert("MBP Parser Thread", err_msg))
            except Exception as alert_err:
                print(f"[MBP] Failed to send Telegram alert (thread): {alert_err}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
