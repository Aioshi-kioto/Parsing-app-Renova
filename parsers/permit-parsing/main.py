"""
Seattle Owner-Builder Tracker
Главный скрипт для запуска системы мониторинга пермитов
"""
import asyncio
from pathlib import Path
from datetime import datetime
from loguru import logger

from config import OUTPUT_DIR, LOGS_DIR, PERMIT_FILTERS
from src.api_client import SeattlePermitsAPI
from src.data_processor import DataProcessor
from src.storage import CSVStorage, get_storage

# Настройка логирования
logger.add(
    LOGS_DIR / "tracker_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO"
)


async def fetch_and_analyze(year: int = 2026, limit: int = 10000) -> Path:
    """
    Основной workflow:
    1. Получение пермитов через API
    2. Фильтрация потенциальных owner-builders
    3. Сохранение для дальнейшей верификации
    """
    logger.info(f"Starting permit fetch for year {year}")
    
    # 1. Получаем данные через API
    api = SeattlePermitsAPI()
    df = await api.fetch_permits(year=year, contractor_is_null=True, limit=limit)
    
    if df.empty:
        logger.warning("No permits found matching criteria")
        return None
    
    logger.info(f"Fetched {len(df)} potential owner-builder permits")
    
    # 2. Обрабатываем данные
    processor = DataProcessor(df)
    
    # Удаляем ненужные поля
    processed_df = processor.remove_fields()
    
    # Добавляем поля для верификации
    processed_df = processor.add_verification_status()
    
    # 3. Фильтруем только новые (ещё не обработанные)
    storage = CSVStorage()
    new_permits_df = storage.filter_new_permits(processed_df)
    
    if new_permits_df.empty:
        logger.info("No new permits to process")
        return None
    
    # 4. Сохраняем для верификации
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"permits_to_verify_{timestamp}.csv"
    new_permits_df.to_csv(output_file, index=False)
    
    # Статистика
    stats = processor.get_stats()
    logger.info(f"Statistics: {stats}")
    
    logger.info(f"Saved {len(new_permits_df)} permits to {output_file}")
    
    return output_file


async def verify_permits(input_file: Path, max_permits: int = 50) -> Path:
    """
    Верификация пермитов через Playwright:
    1. Загрузка списка пермитов
    2. Проверка каждого на портале Accela
    3. Сохранение подтверждённых owner-builders
    """
    try:
        from src.browser_scraper import AccelaScraper
    except ImportError:
        logger.error("Playwright not available. Install with: pip install playwright playwright-stealth")
        return None
    
    logger.info(f"Starting verification from {input_file}")
    
    # Загружаем пермиты для проверки
    processor = DataProcessor()
    df = processor.load_csv(input_file)
    
    if "permitnum" not in df.columns:
        logger.error("No permitnum column found")
        return None
    
    permit_nums = df["permitnum"].head(max_permits).tolist()
    logger.info(f"Will verify {len(permit_nums)} permits")
    
    # Инициализируем скрапер
    scraper = AccelaScraper()
    await scraper.init_browser()
    
    try:
        # Верифицируем пакетом
        results = await scraper.verify_batch(permit_nums)
        
        # Обрабатываем результаты
        owner_builders = []
        for result in results:
            if result.is_owner_builder:
                owner_builders.append({
                    "permitnum": result.permit_num,
                    "work_performer": result.work_performer,
                    "owner_name": result.owner_name,
                    "owner_address": result.owner_address,
                })
                logger.info(f"Found owner-builder: {result.permit_num}")
        
        logger.info(f"Verified {len(results)} permits, found {len(owner_builders)} owner-builders")
        
        # Сохраняем результаты
        if owner_builders:
            import pandas as pd
            results_df = pd.DataFrame(owner_builders)
            
            # Объединяем с исходными данными
            merged_df = df[df["permitnum"].isin(results_df["permitnum"])].merge(
                results_df, on="permitnum", how="left"
            )
            
            storage = CSVStorage()
            output_file = storage.save_owner_builders(merged_df)
            
            # Помечаем как обработанные
            storage.mark_processed(df[df["permitnum"].isin(permit_nums)])
            
            return output_file
        
    finally:
        await scraper.close()
    
    return None


def quick_analysis():
    """Быстрый анализ данных без Playwright"""
    api = SeattlePermitsAPI()
    
    # Синхронная версия для простого запуска
    df = api.fetch_permits_sync(year=2026, contractor_is_null=True, limit=1000)
    
    print(f"\n{'='*60}")
    print(f"Seattle Owner-Builder Analysis")
    print(f"{'='*60}")
    print(f"\nTotal permits without contractor: {len(df)}")
    
    # Анализ
    processor = DataProcessor(df)
    stats = processor.get_stats()
    
    print(f"\nDate range: {stats.get('date_range')}")
    print(f"Average project cost: ${stats.get('avg_project_cost', 0):,.2f}")
    
    if "permitclass" in df.columns:
        print(f"\nPermit classes:")
        for cls, count in df["permitclass"].value_counts().items():
            print(f"  - {cls}: {count}")
    
    # Сохраняем сырые данные
    raw_file = OUTPUT_DIR / "raw_permits_analysis.csv"
    df.to_csv(raw_file, index=False)
    print(f"\nRaw data saved to: {raw_file}")
    
    # Очищенные данные
    clean_df = processor.remove_fields()
    clean_file = OUTPUT_DIR / "clean_permits_analysis.csv"
    clean_df.to_csv(clean_file, index=False)
    print(f"Clean data saved to: {clean_file}")
    
    return df


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "fetch":
            # Только получение данных
            asyncio.run(fetch_and_analyze())
            
        elif command == "verify":
            # Верификация существующего файла
            if len(sys.argv) > 2:
                input_file = Path(sys.argv[2])
                asyncio.run(verify_permits(input_file))
            else:
                print("Usage: python main.py verify <input_file.csv>")
                
        elif command == "analyze":
            # Быстрый анализ
            quick_analysis()
            
        else:
            print("Unknown command. Use: fetch, verify, analyze")
    else:
        # По умолчанию - быстрый анализ
        print("Running quick analysis...")
        print("Use 'python main.py fetch' for full workflow")
        print("Use 'python main.py analyze' for quick analysis")
        quick_analysis()
