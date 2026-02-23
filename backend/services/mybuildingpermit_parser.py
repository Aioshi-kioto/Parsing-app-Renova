"""
MyBuildingPermit Parser Service
Использует parsers/mybuildingpermit-parsing — адаптивные даты (7→6→5...), дедупликация, БД
"""
import asyncio
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

import sys
from pathlib import Path
# Добавляем parsers/mybuildingpermit-parsing в path
PROJECT_ROOT = Path(__file__).parent.parent.parent
PARSER_PATH = PROJECT_ROOT / "parsers" / "mybuildingpermit-parsing"
sys.path.insert(0, str(PARSER_PATH))

from database import update_mbp_job, insert_mbp_permit, get_connection


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
    from src.scraper import MyBuildingPermitScraper

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
        )

        # Сохраняем в БД (insert_mbp_permit уже дедуплицирует по permit_number,jurisdiction)
        total_count = len(results)
        matching_count = sum(1 for r in results if r.matches_target_type)
        owner_count = sum(1 for r in results if r.is_owner_builder)
        print(f"[MBP] Job {job_id}: Saving {total_count} permits (total: {total_count}, matching types: {matching_count}, owner-builders: {owner_count})...")
        saved_count = 0
        for r in results:
            if r.permit_number and not r.error:
                insert_mbp_permit(job_id, r.to_dict())
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
        
        # Если задача была отменена, не помечаем как failed
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
            err_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[MBP] Job {job_id} FAILED (thread): {err_msg}")
            traceback.print_exc()
            update_mbp_job(
                job_id,
                status="failed",
                error_message=err_msg,
                completed_at=datetime.now().isoformat(),
                current_jurisdiction=None,
            )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
