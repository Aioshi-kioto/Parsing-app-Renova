# Seattle Owner-Builder Tracker

Автоматизированный сервис для поиска «самостроев» в Сиэтле. Система фильтрует новые разрешения на строительство и выявляет те, где работы планирует выполнять сам владелец (Owner), а не нанятая компания.

## Структура проекта

```
permit-parsing/
├── config.py              # Конфигурация и настройки
├── main.py                # Главный скрипт запуска
├── download_and_analyze.py # Скрипт загрузки и анализа
├── requirements.txt       # Зависимости Python
├── .env.example          # Пример переменных окружения
├── src/
│   ├── __init__.py
│   ├── api_client.py     # Клиент Socrata SODA API
│   ├── browser_scraper.py # Playwright scraper для Accela
│   ├── data_processor.py  # Обработка данных
│   └── storage.py        # CSV/PostgreSQL хранилище
├── data/                 # Сырые данные (создаётся автоматически)
├── output/               # Результаты (создаётся автоматически)
└── logs/                 # Логи (создаётся автоматически)
```

## Установка

```bash
# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Установка зависимостей
pip install -r requirements.txt

# Установка браузеров Playwright
playwright install chromium
```

## Использование

### 1. Быстрая загрузка и анализ данных

```bash
python download_and_analyze.py
```

Это загрузит данные о пермитах за 2026 год и выполнит базовый анализ.

### 2. Полный workflow

```bash
# Получение данных через API
python main.py fetch

# Верификация через Playwright (требует установки браузеров)
python main.py verify output/permits_to_verify_*.csv

# Быстрый анализ
python main.py analyze
```

## Фильтры данных

По умолчанию применяются следующие фильтры:
- **Класс пермита**: Single Family / Duplex
- **Тип пермита**: Building
- **Год**: 2026
- **Минимальная стоимость**: $5,000
- **Контрактор**: IS NULL (не указан)

## API Источник

Данные получаются из [Seattle Open Data Portal](https://data.seattle.gov/):
- Dataset: Building Permits
- Endpoint: `https://data.seattle.gov/resource/76t5-zqzr.json`
- Documentation: [Socrata SODA API](https://dev.socrata.com/docs/endpoints.html)

## Accela Portal

Верификация статуса owner-builder выполняется через:
- URL: `https://cosaccela.seattle.gov/portal/`
- Секция: Contractor Disclosure
- Поле: "Who will be performing all the work?"

## Результаты

Итоговый CSV файл содержит:
- Адрес объекта
- Номер пермита
- Имя владельца
- Стоимость проекта
- Дата подачи заявки
- Статус верификации
