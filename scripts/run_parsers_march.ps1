# run_parsers_march.ps1
# Запуск двух парсеров через Backend API (не старый код из parsers/).
# Бэкенд должен быть запущен: python start.py (смотри порт в выводе "Backend API: http://localhost:XXXX").
#
# Кто что парсит:
#   1) SDCI  = только Сиэтл (data.seattle.gov), март 2026, верификация owner-builder через портал.
#   2) MBP   = 3 города (Сиэтла в MBP нет): Bellevue, Kirkland, Sammamish
#              (permitsearch.mybuildingpermit.com), последние 30 дней.
#
# Проверка по шагам:
#   Шаг 1 — Запросы: оба POST должны вернуть 200 и { "status": "started", "job_id": N }.
#   Шаг 2 — Backend: в логах бэкенда [PERMITS API] и [MBP API] старт, затем [JOB N] прогресс; без "cannot import BASE_URL" / "MBP Parser Thread" ошибок.
#   Шаг 3 — UI: Permits — джобы SDCI; MyBuildingPermit — джобы MBP и таблица owner-builders после успешного завершения.
#   Шаг 4 — Telegram: два старта (SDCI, MBP) и два завершения (если TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env).

$ErrorActionPreference = "Stop"
# Порт бэкенда (start.py выводит "Backend API: http://localhost:XXXX")
$BaseUrl = "http://localhost:8001"

function Invoke-Parse {
    param(
        [string] $Name,
        [string] $Uri,
        [hashtable] $Body
    )
    Write-Host ""
    Write-Host "[$Name] Sending request to $Uri ..." -ForegroundColor Cyan
    try {
        $json = $Body | ConvertTo-Json
        $response = Invoke-RestMethod -Uri $Uri -Method Post -Body $json -ContentType "application/json" -TimeoutSec 30
        Write-Host "[$Name] OK Started. Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Green
        return $response
    } catch {
        Write-Host "[$Name] ERROR: $_" -ForegroundColor Red
        throw
    }
}

# 1) SDCI — март 2026, headless
$sdciBody = @{
    year                 = 2026
    month                = 3
    permit_class         = "Single Family / Duplex"
    min_cost             = 5000
    verify_owner_builder = $true
    headless             = $true
}
Invoke-Parse -Name "SDCI" -Uri "$BaseUrl/api/permits/parse" -Body $sdciBody

# 2) MyBuildingPermit — 3 города (Сиэтла в MBP нет), последние 30 дней, headless
$mbpJurisdictions = @("Bellevue", "Kirkland", "Sammamish")
$mbpBody = @{
    jurisdictions   = $mbpJurisdictions
    days_back       = 30
    limit_per_city  = $null
    headless        = $true
}
Invoke-Parse -Name "MyBuildingPermit" -Uri "$BaseUrl/api/mybuildingpermit/parse" -Body $mbpBody

Write-Host ""
Write-Host "Both parsers started. Check Telegram for notifications and backend logs for progress." -ForegroundColor Green
Write-Host "Jobs: SDCI and MBP run in background; use the app UI (Permits / MyBuildingPermit) to see status." -ForegroundColor Gray
