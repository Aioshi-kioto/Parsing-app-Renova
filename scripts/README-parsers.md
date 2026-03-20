# Запуск парсеров через Backend API

Парсеры **не запускаются** из старых папок `parsers/` напрямую. Рабочий способ:

1. **Запустить backend** (тот же, что и для UI):
   ```bash
   python start.py
   ```
   или только бэкенд: `python start.py --backend`

2. **Сделать запрос к API** — так же, как делает UI при нажатии «Запустить».

**Кто что парсит:**
- **SDCI (Permits)** — только **Сиэтл** (data.seattle.gov), выбранный месяц/год, верификация owner-builder.
- **MBP (MyBuildingPermit)** — **13 юрисдикций** (не Сиэтл): Auburn, Bellevue, Bothell, Burien, Edmonds, Kenmore, King County, Kirkland, Mercer Island, Mill Creek, Newcastle, Sammamish, Snoqualmie (permitsearch.mybuildingpermit.com).

## Варианты запроса

### PowerShell (Windows)
```powershell
.\scripts\run_parsers_march.ps1
```
Скрипт шлёт два POST на `http://localhost:8000` (порт можно поменять в начале файла).

### curl — SDCI (март 2026)
```bash
curl -X POST http://localhost:8000/api/permits/parse \
  -H "Content-Type: application/json" \
  -d '{"year":2026,"month":3,"permit_class":"Single Family / Duplex","min_cost":5000,"verify_owner_builder":true,"headless":true}'
```

### curl — MyBuildingPermit (30 дней, все юрисдикции)
```bash
curl -X POST http://localhost:8000/api/mybuildingpermit/parse \
  -H "Content-Type: application/json" \
  -d '{"jurisdictions":["Auburn","Bellevue","Bothell","Burien","Edmonds","Kenmore","King County","Kirkland","Mercer Island","Mill Creek","Newcastle","Sammamish","Snoqualmie"],"days_back":30,"limit_per_city":null,"headless":true}'
```

Backend запустит те же сервисы, что и UI; уведомления в Telegram уйдут, если в `.env` заданы `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`.

---

## Проверка по шагам

| Шаг | Что проверить |
|-----|----------------|
| **1. Запросы** | Оба POST возвращают 200 и `{ "status": "started", "job_id": N }`. Если ошибка — неверный порт или бэкенд не запущен. |
| **2. Backend** | В логах терминала с `python start.py`: `[PERMITS API]` и `[MBP API]` старт, затем прогресс `[JOB N]`. Нет ошибок вида `cannot import name 'BASE_URL'` или `MBP Parser Thread`. |
| **3. UI** | Страница Permits — джобы SDCI и пермиты. Страница MyBuildingPermit — джобы MBP и таблица owner-builders после успешного завершения. |
| **4. Telegram** | Четыре сообщения: два «Запуск парсера» (SDCI, MBP) и два «Парсер завершен» (если оба джоба дошли до конца). |
