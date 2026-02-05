# Seattle Owner-Builder Tracker — Master Specification

> **Версия:** 1.0  
> **Дата:** 2026-01-29  
> **Статус:** Active

---

## 1. Обзор проекта

**Цель:** Автоматизированный поиск строительных пермитов в Сиэтле, где владелец планирует выполнять работы самостоятельно (Owner-Builder), а не через лицензированного подрядчика.

**Бизнес-ценность:** Выявление потенциальных клиентов для услуг строительного консалтинга, материалов или субподряда.

---

## 2. Модель данных

### 2.1 Источник данных

| Параметр | Значение |
|----------|----------|
| **Датасет** | Building Permits |
| **ID** | `76t5-zqzr` |
| **Портал** | [data.seattle.gov](https://data.seattle.gov/Built-Environment/Building-Permits/76t5-zqzr) |
| **API Endpoint** | `https://data.seattle.gov/resource/76t5-zqzr.json` |
| **CSV Endpoint** | `https://data.seattle.gov/resource/76t5-zqzr.csv` |
| **Документация API** | [dev.socrata.com](https://dev.socrata.com/foundry/data.seattle.gov/76t5-zqzr) |

### 2.2 Характеристики датасета

- **Тип:** Единый живой датасет (не отдельные выгрузки по дням)
- **Размер:** 180,000+ записей (исторические данные с 2005 года)
- **Обновление:** Ежедневно (новые пермиты добавляются по мере подачи)
- **Формат:** JSON / CSV через SODA API

### 2.3 Ключевые поля

| Поле | Тип | Описание | Использование |
|------|-----|----------|---------------|
| `permitnum` | string | Уникальный номер пермита | Primary Key |
| `applieddate` | datetime | Дата подачи заявки | Фильтрация по периоду |
| `permitclass` | string | Класс пермита | Фильтр: Single Family/Duplex |
| `permittypemapped` | string | Тип пермита | Фильтр: Building |
| `estprojectcost` | number | Оценочная стоимость | Фильтр: > $5,000 |
| `contractorcompanyname` | string | Имя подрядчика | Фильтр: IS NULL |
| `originaladdress1` | string | Адрес объекта | Выходные данные |
| `description` | string | Описание работ | Выходные данные |
| `statuscurrent` | string | Текущий статус | Информационное |
| `latitude` / `longitude` | number | Координаты | Геолокация |
| `link` | object | Ссылка на портал | Верификация |

### 2.4 Значения permitclass

```
- "Single Family/Duplex"  <- Целевой класс
- "Commercial"
- "Multifamily"
- "Institutional"
- "Industrial"
- "N/A"
```

---

## 3. Стратегия загрузки данных

### 3.1 Принцип

**НЕ скачиваем** весь CSV (180k+ строк) каждый раз.

**Используем инкрементальные запросы:**
- Запрашиваем только записи за определённый период
- Фильтруем на стороне API (не локально)
- Храним `last_run_date` для отслеживания прогресса

### 3.2 SODA API Query

**Базовый endpoint:**
```
https://data.seattle.gov/resource/76t5-zqzr.json
```

**Параметры запроса:**

| Параметр | Описание |
|----------|----------|
| `$where` | SoQL условие фильтрации |
| `$limit` | Максимум записей (default: 1000, max: 50000) |
| `$offset` | Смещение для пагинации |
| `$order` | Сортировка |
| `$$app_token` | API токен (опционально) |

### 3.3 SoQL фильтр (бизнес-логика)

```sql
applieddate >= '{start_date}'
AND applieddate < '{end_date}'
AND permitclass = 'Single Family/Duplex'
AND permittypemapped = 'Building'
AND estprojectcost > 5000
AND contractorcompanyname IS NULL
```

**Пример полного URL:**
```
https://data.seattle.gov/resource/76t5-zqzr.json?$where=applieddate >= '2026-01-01' AND permitclass = 'Single Family/Duplex' AND permittypemapped = 'Building' AND estprojectcost > 5000 AND contractorcompanyname IS NULL&$limit=10000&$order=applieddate DESC
```

### 3.4 Rate Limits

| Режим | Лимит | Рекомендация |
|-------|-------|--------------|
| Без токена | ~1000 запросов/час | Для разработки и тестирования |
| С токеном | Выше | Для продакшена |

**Получить токен:** [dev.socrata.com/register](https://dev.socrata.com/register)

---

## 4. Алгоритм еженедельного обновления

### 4.1 Входные данные

- `last_run_date` — дата предыдущего успешного запуска (хранится в `data/state.json`)
- Конфигурация фильтров (см. раздел 3.3)

### 4.2 Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    WEEKLY UPDATE WORKFLOW                    │
└─────────────────────────────────────────────────────────────┘

1. INIT
   ├── Загрузить state.json
   ├── start_date = last_run_date (или now - 7 days если первый запуск)
   └── end_date = now()

2. FETCH
   ├── Сформировать SoQL запрос с фильтрами
   ├── GET https://data.seattle.gov/resource/76t5-zqzr.json
   └── Сохранить в staging (data/staging.csv)

3. DEDUPLICATE
   ├── Загрузить master_owner_builders.csv
   ├── Найти новые permitnum (отсутствующие в master)
   └── Отфильтровать только новые записи

4. VERIFY (Playwright)
   ├── Для каждого нового permitnum:
   │   ├── Открыть страницу Accela Portal
   │   ├── Найти секцию "Contractor Disclosure"
   │   ├── Прочитать "Who will be performing all the work?"
   │   │
   │   ├── IF содержит "Owner" → is_owner_builder = TRUE
   │   └── IF содержит "Licensed Contractor" → is_owner_builder = FALSE
   │
   └── Сохранить результат верификации

5. SAVE
   ├── Добавить верифицированных owner-builders в master CSV
   ├── Обновить state.json: last_run_date = end_date
   └── Сгенерировать daily/weekly report

6. CLEANUP
   └── Удалить staging файлы
```

### 4.3 Структура state.json

```json
{
  "last_run_date": "2026-01-29",
  "last_run_timestamp": "2026-01-29T09:00:00.000Z",
  "total_processed": 4582,
  "total_verified_owners": 342,
  "version": "1.0"
}
```

---

## 5. Верификация через Accela Portal

### 5.1 Портал

| Параметр | Значение |
|----------|----------|
| **URL** | `https://cosaccela.seattle.gov/portal/` |
| **Страница пермита** | `https://cosaccela.seattle.gov/portal/cap/capDetail.aspx?...&permitNumber={permitnum}` |

### 5.2 Целевая секция

**Contractor Disclosure** → поле **"Who will be performing all the work?"**

![Contractor Disclosure Section](../assets/contractor_disclosure_example.png)

### 5.3 Логика определения

```python
def is_owner_builder(text: str) -> bool:
    text_lower = text.lower()
    
    # Явные индикаторы owner-builder
    if "owner" in text_lower:
        if "licensed contractor" not in text_lower:
            return True
    
    # Явный индикатор подрядчика
    if "licensed contractor" in text_lower:
        return False
    
    # Неопределённо - требует ручной проверки
    return None
```

### 5.4 Stealth режим

Для обхода защиты портала:
- `playwright-stealth` — эмуляция реального браузера
- Резидентные прокси (опционально)
- Рандомизация задержек между запросами (2-5 сек)
- User-Agent ротация

---

## 6. Структура репозитория

```
permit-parsing/
│
├── docs/
│   └── master_spec.md          # Этот документ
│
├── src/
│   ├── __init__.py
│   ├── fetch_permits.py        # Модуль загрузки данных из API
│   ├── check_owner_playwright.py  # Верификация через Accela
│   ├── data_processor.py       # Обработка и очистка данных
│   └── storage.py              # Работа с файлами и БД
│
├── data/
│   ├── state.json              # Состояние (last_run_date)
│   ├── staging.csv             # Временные данные
│   └── master_owner_builders.csv  # Итоговая база owner-builders
│
├── output/
│   └── reports/                # Ежедневные/еженедельные отчёты
│
├── config.py                   # Конфигурация проекта
├── main.py                     # Точка входа
├── daily_update.py             # Скрипт ежедневного обновления
├── requirements.txt            # Python зависимости
└── README.md                   # Краткое описание проекта
```

---

## 7. Выходные данные

### 7.1 Состав полей (только эти колонки)

В финальных CSV и Excel **оставляем только** следующие 15 полей. Все остальные поля из API **удаляются**.

| Колонка (Excel/CSV) | API-поле | Описание |
|---------------------|----------|----------|
| PermitNum | `permitnum` | Номер пермита (PK) |
| PermitClass | `permitclass` | Класс пермита |
| PermitClassMapped | `permitclassmapped` | Класс (маппинг) |
| PermitTypeMapped | `permittypemapped` | Тип пермита |
| PermitTypeDesc | `permittypedesc` | Описание типа |
| Description | `description` | Описание работ |
| EstProjectCost | `estprojectcost` | Оценочная стоимость |
| AppliedDate | `applieddate` | Дата подачи |
| OriginalAddress1 | `originaladdress1` | Адрес объекта |
| OriginalCity | `originalcity` | Город |
| OriginalState | `originalstate` | Штат |
| OriginalZip | `originalzip` | Индекс |
| ContractorCompanyName | `contractorcompanyname` | Подрядчик (если указан) |
| Link | `link` | Ссылка на портал |
| HousingCategory | `housingcategory` | Категория жилья |

**Список полей для кода (остальное удалять):**

```python
FIELDS_TO_KEEP = {
    "permitnum": "PermitNum",
    "permitclass": "PermitClass",
    "permitclassmapped": "PermitClassMapped",
    "permittypemapped": "PermitTypeMapped",
    "permittypedesc": "PermitTypeDesc",
    "description": "Description",
    "estprojectcost": "EstProjectCost",
    "applieddate": "AppliedDate",
    "originaladdress1": "OriginalAddress1",
    "originalcity": "OriginalCity",
    "originalstate": "OriginalState",
    "originalzip": "OriginalZip",
    "contractorcompanyname": "ContractorCompanyName",
    "link": "Link",
    "housingcategory": "HousingCategory",
}
```

### 7.2 Удаляемые поля

Все поля, **не входящие** в список выше, из финального набора удаляются. В их числе (примеры): `latitude`, `longitude`, `location1`, `statuscurrent`, `housingunits`, `issueddate`, `expiresdate`, `completeddate`, `relatedmup`, `zoning`, `dwellingunittype`, `parentpermitnum`, все поля с датами ревью и т.д.

Очистка выполняется при экспорте в CSV/Excel (скрипт `csv_to_excel.py`) и при сохранении master-файлов в пайплайне.

### 7.3 Экспорт в Excel

Файл `output/seattle_permits_review.xlsx` формируется скриптом `csv_to_excel.py`:

- Только перечисленные в 7.1 поля.
- Оформление: заголовки — жирный шрифт, синий фон, белый текст; фиксированная ширина колонок; заморозка первой строки; автофильтр по всем колонкам.
- Формат чисел: `EstProjectCost` — с разделителем тысяч; `AppliedDate` — дата.

---

## 8. Конфигурация

### 8.1 Переменные окружения (.env)

```env
# API
SOCRATA_APP_TOKEN=           # Опционально, для высокой нагрузки
SOCRATA_DOMAIN=data.seattle.gov
SOCRATA_DATASET_ID=76t5-zqzr

# Playwright
HEADLESS=true
MAX_CONCURRENT_BROWSERS=3
REQUEST_DELAY_MS=2000

# Proxy (опционально)
PROXY_URL=
PROXY_USERNAME=
PROXY_PASSWORD=

# Database (опционально)
DATABASE_URL=postgresql://...
```

### 8.2 Бизнес-параметры (config.py)

```python
PERMIT_FILTERS = {
    "permit_class": ["Single Family/Duplex"],
    "permit_type": "Building",
    "min_cost": 5000,
    "contractor_is_null": True,
}

DEFAULT_LOOKBACK_DAYS = 7  # Период по умолчанию
MAX_RECORDS_PER_REQUEST = 10000
```

---

## 9. Запуск

### 9.1 Установка

```bash
# Клонировать репозиторий
cd permit-parsing

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Установить браузеры Playwright
playwright install chromium
```

### 9.2 Команды

```bash
# Ежедневное/еженедельное обновление
python daily_update.py

# Полный цикл с верификацией
python main.py fetch      # Только загрузка
python main.py verify     # Только верификация
python main.py full       # Полный цикл

# Анализ данных
python main.py analyze
```

### 9.3 Автоматизация (Windows Task Scheduler)

```powershell
# Создать задачу для запуска каждый понедельник в 9:00
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "daily_update.py" `
    -WorkingDirectory "C:\path\to\permit-parsing"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am

Register-ScheduledTask `
    -TaskName "SeattlePermitsWeeklyUpdate" `
    -Action $action `
    -Trigger $trigger
```

---

## 10. Результаты тестирования (2026-01-30)

### 10.1 Стек и инструменты

| Компонент | Версия | Статус |
|-----------|--------|--------|
| Python | 3.11 | OK |
| Playwright | 1.41.0 | OK |
| playwright-stealth | 1.0.6 | OK (sync не используется) |
| httpx | 0.27.0+ | OK |
| pandas | 2.2.0+ | OK |
| openpyxl | latest | OK |

### 10.2 Тест на 5 ссылках

**Дата:** 2026-01-30  
**URL формат:** `https://services.seattle.gov/portal/customize/LinkToRecord.aspx?altId={permitnum}`

| Параметр | Результат |
|----------|-----------|
| HTTP статус | 200 (все 5) |
| Страница загружается | Да |
| Секция "Contractor Disclosure" | Найдена на всех |
| Поле "Who will be performing all the work?" | Извлекается корректно |
| Защита (captcha, блокировка) | **Не обнаружена** |

**Вывод:** Playwright работает без блокировок, данные извлекаются.

### 10.3 Полный скрейп января 2026

| Метрика | Значение |
|---------|----------|
| Всего записей | 324 |
| **OWNER-BUILDERS** | **59 (18.2%)** |
| Contractors | 119 (36.7%) |
| Unknown/Без данных | 80 (24.7%) |
| Ошибки сети | 66 (20.4%) |

**Статистика Owner-Builders:**

| Метрика | Значение |
|---------|----------|
| Количество | 59 |
| Средняя стоимость | $285,291 |
| Медиана | $217,507 |
| Минимум | $8,000 |
| Максимум | $1,000,000 |
| **Общая стоимость** | **$16,832,144** |

### 10.4 Причины Unknown/Errors

1. **Ошибки сети (66):** `ERR_NETWORK_IO_SUSPENDED` — временные проблемы соединения, решается повторным запуском.
2. **Без данных (80):** Секция "Contractor Disclosure" не заполнена — пермиты в процессе оформления.

### 10.5 Выходные файлы

| Файл | Описание | Записей |
|------|----------|---------|
| `output/FINAL_owner_builders_jan2026.xlsx` | Excel с owner-builders для ручной проверки | 59 |
| `output/FINAL_owner_builders_jan2026.csv` | CSV версия | 59 |
| `output/jan2026_all_results.csv` | Все результаты скрейпинга | 324 |
| `output/jan2026_owners_only.csv` | Только owners (полные данные) | 59 |

### 10.6 Логика определения Owner-Builder

```python
def is_owner_builder(work_performer_text):
    text = work_performer_text.lower()
    
    # Если есть "owner" и НЕТ "licensed contractor" → Owner
    if "owner" in text and "licensed contractor" not in text:
        return True
    
    # Если есть "licensed contractor" → Contractor
    if "licensed contractor" in text:
        return False
    
    # Иначе — неопределённо
    return None
```

**Типичные значения поля:**
- `"Owner/Lessee"` → Owner-Builder ✓
- `"Licensed Contractor"` → Contractor ✗

---

## 11. Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-01-29 | Начальная версия спецификации |
| 1.1 | 2026-01-30 | Добавлены результаты тестирования Playwright, обновлён список полей |

---

## 12. Ссылки

- [Seattle Open Data Portal](https://data.seattle.gov/)
- [Building Permits Dataset](https://data.seattle.gov/Built-Environment/Building-Permits/76t5-zqzr)
- [Socrata SODA API Docs](https://dev.socrata.com/docs/endpoints.html)
- [Seattle Services Portal (Accela)](https://cosaccela.seattle.gov/portal/)
- [Playwright Python Docs](https://playwright.dev/python/)
