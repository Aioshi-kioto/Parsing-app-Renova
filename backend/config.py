import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Fallback для парсера MBP: при разрешении config в backend (cwd/пути) скрапер ищет BASE_URL
BASE_URL = "https://permitsearch.mybuildingpermit.com"

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://renova:password@localhost:5432/renova"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Exteral APIs
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    LOB_API_KEY: str = ""
    APOLLO_API_KEY: str = ""
    PROXY_URL: str = ""  # Для MyBuildingPermit Playwright парсера
    FRONTEND_URL: str = "https://google.com"  # Ссылка на Дашборд для кнопок в боте

    # Добавляем загрузку из .env, находящегося в корне
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
