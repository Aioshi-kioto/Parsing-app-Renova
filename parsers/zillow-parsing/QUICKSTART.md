# Быстрый старт — Веб-интерфейс

## Запуск одной командой

Скрипт проверяет и устанавливает зависимости, затем запускает backend и frontend:

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh

# Python
python start.py
```

Открой http://localhost:5173

## Альтернативные способы запуска

### Через npm (из папки frontend)

```bash
cd frontend
npm install   # первый раз
npm start    # backend + frontend
```

### Ручной запуск (два терминала)

**Терминал 1 — Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Терминал 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Использование

1. Открой http://localhost:5173
2. Разверни инструкцию по получению URL
3. Вставь URL из Zillow (по одному на строку)
4. Нажми «Запустить парсинг»
5. При первом запросе откроется браузер — пройди капчу
6. Следи за прогрессом в интерфейсе
7. После завершения — экспорт в CSV из истории

## Важно

- Приложение работает **локально** (браузер для капчи открывается на твоей машине)
- Backend: порт 8000
- Frontend: порт 5173
- БД: `backend/data/zillow.db` (создаётся автоматически)

## Порт 8000 занят

Если ошибка «доступ к сокету запрещён» — порт 8000 занят. Запусти с другим портом:

```bash
# Windows
set BACKEND_PORT=8001
python start.py

# Linux/Mac
BACKEND_PORT=8001 python start.py
```

И обнови `frontend/vite.config.js`: в proxy target укажи `http://localhost:8001`
