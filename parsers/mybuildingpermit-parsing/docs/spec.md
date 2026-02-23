# MyBuildingPermit — техническая спецификация

## 1. Сайт

| Параметр | Значение |
|----------|----------|
| **URL** | https://permitsearch.mybuildingpermit.com/ |
| **Фреймворк** | ASP.NET |
| **UI** | Kendo UI Grid (Telerik) |
| **Рендеринг** | Server-Side |
| **Документация** | [Status Site User Guide](https://mybuildingpermit.com/sites/default/files/documentation/Status%20Site%20User%20Guide%20Final.pdf) |

---

## 2. Ограничения

| Правило | Значение |
|---------|----------|
| **Макс. результатов** | **100** — при превышении ошибка, нужно сужать поиск |
| **Обязательное поле** | Jurisdiction (кнопка Search отключена до выбора) |
| **Табы поиска** | Критерии из одного таба **не переносятся** в другой |

---

## 3. Четыре режима поиска (Search by)

### 3.1 Permit #

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| Permit Number | Text | Да | Partial match, можно часть номера |
| Date Type | Radio | Нет | Applied / Issued / Finaled |
| From / To | Date | Нет | Требуется Date Type |

### 3.2 Project Info

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| Project Name/Description | Text | Минимум 1 | Partial match |
| **Permit Type** | Multi-select | Минимум 1 | **Зависит от Jurisdiction** |
| **Permit Status** | Multi-select | Минимум 1 | **Зависит от Jurisdiction** |

**Важно:** Permit Type и Status — **jurisdiction-specific**. Smart search: ввод первых букв (напр. MECH → MECHANICAL). Множественный выбор. Иконка `?` рядом — подсказки.

### 3.3 Location

| Поле | Тип | Описание |
|------|-----|----------|
| House/Building Number | Text | Partial match |
| Street Name | Text | Partial match |
| Parcel | Text | Partial match |

**Минимум одно поле.** Partial match — вернёт все адреса, содержащие введённую часть.

### 3.4 People

| Поле | Тип | Описание |
|------|-----|----------|
| Contractor Company | Text | Partial match |
| Contractor License | Text | Partial match |
| Applicant Last Name | Text | Partial match |

**Минимум одно поле.** Partial match по имени.

---

## 4. Общие поля (все табы)

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| **Jurisdiction** | Select | **Да** | См. список ниже |
| Date Type | Radio | Нет | Applied / Issued / Finaled |
| From | Date | Нет | Для Date Type |
| To | Date | Нет | Для Date Type |

---

## 5. Jurisdictions (eCityGov Alliance)

```
Auburn, Bellevue, Bothell, Burien, Edmonds, Federal Way,
Issaquah, Kenmore, King County, Kirkland, Mercer Island,
Mill Creek, Newcastle, Sammamish, Snoqualmie
```

---

## 6. Рекомендуемые фильтры для Owner-Builder (лиды)

**Цель:** пермиты без подрядчика (потенциальные owner-builder).

### Проблема

Форма **не умеет** искать "Contractor = пусто". Нужно искать широко и фильтровать результаты.

### Стратегия

| Шаг | Действие |
|-----|----------|
| 1 | **Search by:** Project Info |
| 2 | **Jurisdiction:** выбрать город (или итерировать все) |
| 3 | **Permit Type:** Building, Single Family, Residential (зависит от jurisdiction) |
| 4 | **Permit Status:** Applied, In Review, Issued (по необходимости) |
| 5 | **Date Type:** Applied |
| 6 | **From / To:** диапазон дат (напр. 2026-01-01 … 2026-02-01) |
| 7 | Запуск поиска → max 100 результатов |
| 8 | **Пост-фильтр:** в результатах/детали отбросить строки, где Contractor ≠ пусто |

### Дополнительно

- **Разбивка по датам:** если пермитов >100, сужать диапазон (неделя/месяц).
- **Permit Type по jurisdiction:** значения разные. Примеры: Building, Single Family, Residential, New Construction.
- **Export:** результаты можно экспортировать в CSV.

---

## 7. Флоу поиска и результаты

### 7.1 Последовательность действий

| Шаг | Действие |
|-----|----------|
| 1 | Выбрать **Jurisdiction** (обязательно) |
| 2 | Выбрать **Search by:** Permit # / Project Info / Location / People |
| 3 | Заполнить критерии (Date Type, From/To и т.д.) |
| 4 | Нажать **Search** (`#btnSearch`, `type="submit"`) |
| 5 | Дождаться загрузки → таблица Kendo Grid |

### 7.2 Таблица результатов

| Элемент | Селектор / Описание |
|---------|---------------------|
| Контейнер | `#searchResultsGrid` |
| Строки | `.k-master-row` |
| Колонки | `td[role='gridcell']`: Permit #, Description, Address, Type, Status, Applied Date, … |
| Ссылка на детали | `a[href^="/PermitDetails/"]` внутри первой ячейки |
| Export | Кнопка "Export to Excel" в toolbar |
| Итого | Внизу: "Total: N records" |

### 7.3 Пост-фильтрация по TARGET_CONFIG

Из таблицы нас интересуют **только** пермиты с типами из `TARGET_CONFIG` для данного города:

| Jurisdiction | permit_types (примеры) |
|--------------|-------------------------|
| Auburn | ADDITION, ALTERATIONS |
| Bellevue | WD, BS, BR, DH |
| Bothell | BSF |
| Burien | Residential-Addition, Residential - Remodel |
| Edmonds | SINGLE FAMILY-STRUCTURE ADDITION-ADDITION, SINGLE FAMILY-REMODEL-ALTERATION |
| Kenmore | SINGLE FAMILY |
| King County | Building/Residential Building/Addition-Improvement |
| Kirkland | ADU, BSF |
| Mercer Island, Mill Creek | Building |
| Newcastle | SINGLE FAMILY RESIDENCE |
| Sammamish | BLDG RESIDENTIAL - ADDITION, BLDG RESIDENTIAL - REMODEL/ALTERATION, … |
| Snoqualmie | Residential |

**Фильтрация:** сравнивать `permit_type` из строки (колонка Type) с `TARGET_CONFIG[jurisdiction].permit_types` (case-insensitive / нормализация пробелов).

### 7.4 Дополнительно

| Элемент | Описание |
|---------|----------|
| Сортировка | По клику на заголовок (одна колонка) |
| Детали | Клик по Permit Number → Permit Details |

---

## 8. Export to Excel и CSV

### 8.1 Кнопка Export

В таблице результатов поиска и в деталях пермита есть кнопка **"Export to Excel"** (Kendo Grid toolbar).

| Элемент | Селектор |
|---------|----------|
| Search results | `#searchResultsGrid` → toolbar `.k-grid-excel` |
| People grid | `#permitPeopleGrid` → toolbar `.k-grid-excel` |

### 8.2 Формат экспорта (Search Results)

CSV/Excel содержит колонки (разделитель `;`):

| Колонка | Описание |
|---------|----------|
| Permit # | Уникальный код (ALT26-0007, GRA26-0004, …) |
| Description | Описание проекта |
| Address | Адрес |
| Type | Тип пермита |
| Status | Статус |
| Applied Date | Дата подачи |
| Application Expiration | Истечение заявки |
| Issued Date | Дата выдачи |
| Finaled Date | Дата завершения |

**Jurisdiction** в экспорте **нет** — он задаётся при поиске (нужно передавать отдельно).

### 8.3 URL деталей из кода

```
https://permitsearch.mybuildingpermit.com/PermitDetails/{PermitNumber}/{Jurisdiction}
```

Пример: `GRA26-0004` + `Auburn` → `https://permitsearch.mybuildingpermit.com/PermitDetails/GRA26-0004/Auburn`

---

## 9. Детали пермита

| Параметр | Значение |
|----------|----------|
| **URL** | `/PermitDetails/{PermitNumber}/{City}` |
| **Пример** | `https://permitsearch.mybuildingpermit.com/PermitDetails/ALT26-0007/Auburn` |

### 9.1 Секции на странице

- **Information** — Project Name, Jurisdiction, Type, Address, Parcel, Status, Applied/Issued/Finaled Date
- **Description** — текст описания
- **People** — `#permitPeopleGrid`, проверка Contractor License Number (см. ниже)
- **Reviews and Activities**
- **Conditions**
- **Inspections**
- **Fees**
- **Other Permits on Same Parcel**

### 9.2 People — структура таблицы

| Колонка | data-field | Описание |
|---------|------------|----------|
| Type | — | Applicant, Contractor |
| Name | — | Имя/название |
| Contractor License Number | ContractorLicNum | **Ключевое поле** для owner-builder |

**Селектор:** `#permitPeopleGrid tbody tr` или `#permitPeopleGrid .k-grid-content tr`, ячейки `td`: `[0]=Type`, `[1]=Name`, `[2]=Contractor License Number`.

### 9.3 Owner-builder: критерий по People

**Сохраняем пермит** только если:

- **Нет** ни одной строки с `Type=Contractor` и непустым `Contractor License Number`.

**Исключаем пермит**, если:

- Любая строка Contractor имеет номер лицензии (напр. `WESTESF785LH`).

**Примеры:**

| Contractor Name | License | Результат |
|-----------------|---------|-----------|
| — (нет Contractor) | — | **Сохранить** |
| CONTRACTOR UNKNOWN | пусто | **Сохранить** |
| TRACY TAYLOR (Applicant) | пусто | — |
| WESTERN STATES FIRE... | WESTESF785LH | **Исключить** |

---

## 10. Форма (DOM)

- **ID формы:** `permitSearchForm`
- **Кнопка Search:** `type="submit"`
- **Кнопка Cancel:** сброс критериев (кроме Jurisdiction)
- **Контент:** `section.main > div.container.body-content > div.row > div.col-md-12`

---

## 11. TARGET_CONFIG, SEARCH_CONFIG, CONTRACTOR_FILTER

### 11.1 TARGET_CONFIG

Ключ — jurisdiction, значение — список типов пермитов для пост-фильтрации:

```python
TARGET_CONFIG = {
    "Auburn": {"permit_types": ["ADDITION", "ALTERATIONS"], "date_range_days": 3},
    "Bellevue": {"permit_types": ["WD", "BS", "BR", "DH"], "date_range_days": 3},
    "Bothell": {"permit_types": ["BSF"], "date_range_days": 3},
    "Burien": {"permit_types": ["Residential-Addition", "Residential - Remodel"], "date_range_days": 3},
    "Edmonds": {"permit_types": ["SINGLE FAMILY-STRUCTURE ADDITION-ADDITION", "SINGLE FAMILY-REMODEL-ALTERATION"], "date_range_days": 3},
    "Kenmore": {"permit_types": ["SINGLE FAMILY"], "date_range_days": 3},
    "King County": {"permit_types": ["Building/Residential Building/Addition-Improvement"], "date_range_days": 3},
    "Kirkland": {"permit_types": ["ADU", "BSF"], "date_range_days": 3},
    "Mercer Island": {"permit_types": ["Building"], "date_range_days": 3},
    "Mill Creek": {"permit_types": ["Building"], "date_range_days": 3},
    "Newcastle": {"permit_types": ["SINGLE FAMILY RESIDENCE"], "date_range_days": 3},
    "Sammamish": {"permit_types": ["BLDG RESIDENTIAL - ADDITION", "BLDG RESIDENTIAL - ACCESSORY STRUCTURE", "BLDG RESIDENTIAL - REPAIR/DAMAGE", "BLDG RESIDENTIAL - REMODEL/ALTERATION"], "date_range_days": 3},
    "Snoqualmie": {"permit_types": ["Residential"], "date_range_days": 3},
}
```

### 10.2 SEARCH_CONFIG

| Параметр | Значение | Описание |
|----------|----------|----------|
| max_date_range | 7 | Максимальный диапазон дат (дней) |
| min_date_range | 1 | Минимальный диапазон |
| reduce_step | 1 | Уменьшение диапазона при ошибке |
| max_retries | 3 | Попыток при ошибке |
| page_load_timeout | 10000 | Таймаут загрузки (мс) |

### 11.3 CONTRACTOR_FILTER (People section)

Критерии для отбора owner-builder лидов:

| Параметр | Описание |
|----------|----------|
| empty_license | True | Пустое поле Contractor License |
| owner_keywords | OWNER, HOMEOWNER, … | Ключевые слова Owner-Builder |
| exclude_with_license | True | Исключать при наличии лицензии |

### 10.4 PEOPLE_TYPES (маппинг)

| Ключ | Label на странице |
|------|-------------------|
| applicant | Applicant |
| contractor | Contractor |
| owner | Owner |
| architect | Architect |
| engineer | Engineer |

---

## 12. Флоу: CSV → Permit Details → Owner-builder

1. **Вход:** CSV (Export to Excel из Search Results), колонка `Permit #` + Jurisdiction.
2. **Для каждого кода:** `GET PermitDetails/{PermitNumber}/{Jurisdiction}`.
3. **Проверка People:** `#permitPeopleGrid` → нет Contractor с непустым License.
4. **Сохранить:** если проходит фильтр — полная информация (Project Name, Address, Parcel, Status, даты, People).

---

## 13. Рекомендации по парсингу

1. **Playwright** — основной способ (ViewState, Kendo, формы, JavaScript).
2. **Сессия и cookies** — сохранять между запросами.
3. **Паузы** — 2–3 сек между запросами.
4. **Селекторы** — уточнять по живому DOM (ASP.NET генерирует свои ID).
5. **Permit Type/Status** — опции зависят от выбранного Jurisdiction.
6. **Пост-фильтр** — после извлечения строк применять TARGET_CONFIG.
