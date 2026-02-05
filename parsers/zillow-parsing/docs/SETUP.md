# Установка и настройка

## Зависимости

```bash
pip install playwright playwright-stealth
playwright install firefox
```

## ⚠️ playwright-stealth обязателен

**Без `playwright-stealth` Zillow блокирует запросы!**

```bash
pip install playwright-stealth
```

## Проверка stealth

После запуска браузера в логах должно быть:
```
[BROWSER] ✅ navigator.webdriver = undefined (stealth работает)
```

Если видите `navigator.webdriver = True` — stealth не работает, переустановите:
```bash
pip uninstall playwright-stealth
pip install playwright-stealth
```

## Смена IP при блокировке

При сообщении "Access to this page has been denied":
- Перезагрузите роутер (новый IP)
- Или используйте VPN/прокси
- Текущий IP помечен как бот

## Структура проекта

```
zillow-parsing/
├── src/core/           # Библиотека парсинга
├── scripts/parsers/    # Скрипты парсинга
│   ├── parse_from_url.py      # Универсальный — любой URL
│   └── parse_seattle_urls.py # Seattle по готовым URL
├── docs/
├── logs/               # Логи (создаётся автоматически)
└── pyproject.toml
```
