"""Скрипт для запуска backend и frontend одной командой"""
import subprocess
import sys
import time
import os
from pathlib import Path

# Путь к npm (если найден в нестандартном месте)
NPM_CMD = None


def find_npm():
    """Ищет npm в PATH и типичных путях Windows"""
    global NPM_CMD
    
    # Сначала пробуем из PATH (shell=True на Windows помогает найти npm в системном PATH)
    try:
        use_shell = sys.platform == "win32"
        result = subprocess.run(
            "npm --version" if use_shell else ["npm", "--version"],
            capture_output=True, text=True, shell=use_shell
        )
        if result.returncode == 0:
            NPM_CMD = "npm"
            return True
    except (FileNotFoundError, OSError):
        pass
    
    # Windows: типичные пути установки Node.js
    if sys.platform == "win32":
        bases = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "nodejs",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "nodejs",
        ]
        if os.environ.get("APPDATA"):
            bases.append(Path(os.environ["APPDATA"]) / "npm")
        for name in ["npm.cmd", "npm"]:
            for base in bases:
                if base.exists() and (base / name).exists():
                    NPM_CMD = str(base / name)
                    return True
        # Через where
        try:
            where = subprocess.run(["where", "npm"], capture_output=True, text=True)
            if where.returncode == 0 and where.stdout.strip():
                NPM_CMD = where.stdout.strip().split("\n")[0].strip()
                return True
        except (FileNotFoundError, OSError):
            pass
    
    return False


def run_npm(*args, cwd=None):
    """Запускает npm с найденной командой"""
    cmd = NPM_CMD or "npm"
    use_shell = sys.platform == "win32" and " " in str(cmd)
    return subprocess.run([cmd] + list(args), cwd=cwd, shell=use_shell)


def check_and_install_backend_deps():
    """Проверяет и устанавливает backend зависимости"""
    print("Проверка backend зависимостей...")
    
    try:
        import fastapi
        import uvicorn
        print("✅ Backend зависимости установлены")
        return True
    except ImportError:
        print("⚠️  Backend зависимости не найдены, устанавливаю...")
        backend_path = Path(__file__).parent / "backend"
        requirements_file = backend_path / "requirements.txt"
        
        if not requirements_file.exists():
            print("❌ Файл requirements.txt не найден!")
            return False
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True,
                cwd=str(backend_path)
            )
            print("✅ Backend зависимости установлены")
            return True
        except subprocess.CalledProcessError:
            print("❌ Ошибка при установке backend зависимостей")
            return False


def check_and_install_frontend_deps():
    """Проверяет и устанавливает frontend зависимости"""
    print("Проверка frontend зависимостей...")
    
    # Поиск npm (PATH + типичные пути Windows)
    if not find_npm():
        print("❌ npm не найден!")
        print("   Node.js установлен? Проверьте: https://nodejs.org/")
        print("   Если установлен — перезапустите терминал или добавьте nodejs в PATH")
        return False
    
    print("   npm найден:", NPM_CMD or "npm")
    
    frontend_path = Path(__file__).parent / "frontend"
    
    # Проверка node_modules
    if not (frontend_path / "node_modules").exists():
        print("⚠️  Frontend зависимости не найдены, устанавливаю...")
        result = run_npm("install", cwd=str(frontend_path))
        if result.returncode != 0:
            print("❌ Ошибка при установке frontend зависимостей")
            return False
        print("✅ Frontend зависимости установлены")
    else:
        print("✅ Frontend зависимости установлены")
    return True


def check_dependencies():
    """Проверяет и устанавливает все зависимости"""
    print("\n" + "="*60)
    print("Проверка и установка зависимостей")
    print("="*60 + "\n")
    
    if not check_and_install_backend_deps():
        return False
    
    if not check_and_install_frontend_deps():
        return False
    
    print("\n✅ Все зависимости готовы!\n")
    return True


def start_backend():
    """Запускает backend"""
    backend_path = Path(__file__).parent / "backend"
    port = os.environ.get("BACKEND_PORT", "8000")
    print(f"🚀 Запуск backend на http://localhost:{port}")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", port],
        cwd=str(backend_path)
    )


def start_frontend():
    """Запускает frontend"""
    frontend_path = Path(__file__).parent / "frontend"
    cmd = NPM_CMD or "npm"
    # На Windows shell=True — иначе npm не находится в venv-контексте
    use_shell = sys.platform == "win32"
    npm_cmd = f"{cmd} run dev" if use_shell else [cmd, "run", "dev"]
    subprocess.run(npm_cmd, shell=use_shell, cwd=str(frontend_path))


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Запуск Zillow Parser Web UI")
    print("="*60 + "\n")
    
    # Запускаем оба процесса
    import threading
    
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    
    backend_thread.start()
    time.sleep(2)  # Даём backend время запуститься
    frontend_thread.start()
    
    port = os.environ.get("BACKEND_PORT", "8000")
    print("\n✅ Оба сервера запущены!")
    print("📱 Frontend: http://localhost:5173")
    print(f"🔧 Backend API: http://localhost:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print("\nНажмите Ctrl+C для остановки\n")
    
    try:
        # Держим скрипт активным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Остановка серверов...")
        sys.exit(0)
