# MyBuildingPermit Parser

Парсер для [permitsearch.mybuildingpermit.com](https://permitsearch.mybuildingpermit.com/) — единый портал поиска разрешений eCityGov Alliance.

---

## Флоу: Export to Excel → CSV → Owner-builder

1. **Поиск** на сайте: Jurisdiction, Date Type=Applied, From/To (неделя)
2. **Search** → таблица результатов
3. **Export to Excel** — скачать CSV/XLSX
4. **Обработка CSV:** для каждого Permit # открывается `PermitDetails/{PermitNumber}/{Jurisdiction}`
5. **Проверка People:** если Contractor License Number **пуст** для всех Contractor → **owner-builder**, сохраняем
6. **Экспорт** в Excel

---

## Режимы работы

### 1. Поиск по датам (run_test.py)

```bash
python run_test.py
```

### 2. CSV из Export to Excel

```bash
python run_csv.py
# или
python -m src.scraper --csv "data/SearchResults (1).csv" --jurisdiction Auburn
python -m src.scraper --csv "data/permits.csv" --jurisdiction Auburn --all   # все, без фильтра owner-builder
```

---

## People: критерий Owner-builder

| Contractor License | Результат |
|-------------------|-----------|
| Пусто | **Сохранить** |
| CONTRACTOR UNKNOWN + пусто | **Сохранить** |
| WESTESF785LH и т.п. | **Исключить** |

---

## Технологии сайта

| Компонент | Технология |
|-----------|-----------|
| Backend | ASP.NET |
| UI | Kendo UI (Telerik) |
| Рендеринг | Server-Side |
| Форма | `permitSearchForm` |

---

## Ограничения

- **Макс. результатов: 100** — при превышении нужно сужать поиск
- **Jurisdiction** — обязательное поле
- **Табы поиска** — критерии не переносятся между Permit #, Project Info, Location, People

---

## Рекомендуемые фильтры для Owner-Builder (лиды)

**Цель:** пермиты без подрядчика (потенциальные owner-builder).

| Параметр | Значение |
|----------|----------|
| **Search by** | Project Info |
| **Jurisdiction** | Auburn, Bellevue, King County, и т.д. (по одному или итерация) |
| **Permit Type** | Building, Single Family, Residential *(зависит от jurisdiction)* |
| **Permit Status** | Applied, In Review, Issued *(по необходимости)* |
| **Date Type** | Applied |
| **From / To** | 2026-01-01 … 2026-02-01 *(сужать при >100 результатов)* |

**Важно:** форма не поддерживает поиск "Contractor = пусто". Нужно искать широко и отфильтровывать результаты по полю Contractor на странице деталей или в таблице.

---

## Jurisdictions

```
Auburn, Bellevue, Bothell, Burien, Edmonds, Federal Way,
Issaquah, Kenmore, King County, Kirkland, Mercer Island,
Mill Creek, Newcastle, Sammamish, Snoqualmie
```

---

## URL деталей

```
https://permitsearch.mybuildingpermit.com/PermitDetails/{PermitNumber}/{City}
```

Пример: `/PermitDetails/ALT26-0007/Auburn`

---

## Стек парсера

- **Playwright + playwright-stealth** — основной инструмент
- **pandas** — обработка данных

---

## Установка

```bash
cd parsers/mybuildingpermit-parsing
pip install -r requirements.txt
playwright install chromium
```

---

## Использование

```bash
python run_test.py          # поиск по датам
python run_csv.py          # CSV из Export to Excel
python -m src.scraper       # CLI (--csv, --jurisdiction, --test-mode)
```

---

## Документация

- **Полная спецификация:** `docs/spec.md`
- **User Guide:** [Status Site User Guide (PDF)](https://mybuildingpermit.com/sites/default/files/documentation/Status%20Site%20User%20Guide%20Final.pdf)
