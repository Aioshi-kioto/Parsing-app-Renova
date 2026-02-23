# Полная перезагрузка приложения (Troubleshooting)

Если изменения во frontend не подхватываются или что-то «не работает»:

---

## 0. Playwright (верификация Owner-Builder)

Если в логах видишь `Playwright not installed` или верификация пермитов не открывает браузер:

1. Из корня проекта выполни (тот же Python, что запускает backend):

   ```bash
   pip install playwright playwright-stealth
   playwright install chromium
   ```

   На macOS используй `pip3` / `python3` если Python установлен через Homebrew.

2. Либо запусти приложение без `--skip-install`: `python start.py` — скрипт сам поставит Playwright и Chromium при первом запуске.

3. Перезапусти backend после установки.

**Browser visible:** В формах Building Permits и MyBuildingPermit переключатель «Browser visible»: включён = браузер виден при верификации/парсинге (`headless=False`), выключен = браузер скрыт.

**Остановить верификацию/парсинг:** На странице Permits или MyBuildingPermit нажми **Cancel** у текущего джоба — браузер закроется, джоб завершится как отменённый. Закрытие терминала не останавливает backend (он может быть запущен через `start.py` в другом процессе).

---

## 1. Остановить всё

- В терминале, где запущен `python start.py` (или `python3 start.py` на Mac), нажми **Ctrl+C**.
- Убедись, что оба процесса (Backend и Frontend) остановились.

---

## 2. Очистить кэш Vite (опционально)

Удали папку кэша frontend (если есть):

```
frontend/node_modules/.vite
```

---

## 3. Запустить заново

```bash
python start.py
```

На macOS:

```bash
python3 start.py
```

Дождись сообщений:

- `Backend API:  http://localhost:8000`
- `Frontend:     http://localhost:5173`

---

## 4. Обновить страницу в браузере без кэша

- **Вариант А:** Жёсткое обновление: **Ctrl+Shift+R** (Windows/Linux) или **Cmd+Shift+R** (macOS).
- **Вариант Б:** Открой сайт в режиме инкогнито: **Ctrl+Shift+N** (Chrome), перейди на http://localhost:5173 (или нужную страницу).

---

## 5. Проверить консоль браузера

- Нажми **F12** → вкладка **Console**.
- Открой страницу MyBuildingPermit (или другую), выполни действие (например Select All / Clear All).
- Если появятся красные ошибки — скопируй их для отладки.

После этого выбор юрисдикций, счётчики и кнопки должны работать.
