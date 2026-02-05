#!/usr/bin/env python3
"""
Renova Parse CRM - Unified Application Launcher

This script starts both the backend (FastAPI) and frontend (Vite) servers
simultaneously for local development.

Usage:
    python start.py           # Start both servers
    python start.py --backend # Start only backend
    python start.py --frontend # Start only frontend
"""

import subprocess
import sys
import os
import signal
import time
import argparse
from pathlib import Path

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print application banner (ASCII-only for Windows compatibility)."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
  ========================================================
    R E N O V A   P A R S E   C R M   v 1 . 0 . 0
  ========================================================
{Colors.ENDC}""")

def check_requirements():
    """Check if required tools are installed."""
    errors = []
    
    # Check Python version
    if sys.version_info < (3, 9):
        errors.append(f"Python 3.9+ required, got {sys.version}")
    
    # Check if npm/node is available
    try:
        subprocess.run(
            ["node", "--version"], 
            capture_output=True, 
            check=True,
            shell=True if os.name == 'nt' else False
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Node.js not found. Please install Node.js 18+")
    
    return errors

def install_backend_deps():
    """Install Python backend dependencies (checks and installs missing)."""
    print(f"{Colors.BLUE}[Backend]{Colors.ENDC} Checking Python dependencies...")
    
    requirements_file = Path(__file__).parent / "backend" / "requirements.txt"
    if requirements_file.exists():
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-q"],
                check=True
            )
            print(f"{Colors.GREEN}[Backend]{Colors.ENDC} Dependencies OK [OK]")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}[Backend]{Colors.ENDC} Failed to install dependencies: {e}")
            return False
    return True

def install_frontend_deps():
    """Install frontend npm dependencies (checks and installs missing)."""
    print(f"{Colors.CYAN}[Frontend]{Colors.ENDC} Checking npm dependencies...")
    
    frontend_dir = Path(__file__).parent / "frontend"
    try:
        subprocess.run(
            ["npm", "install"],
            cwd=str(frontend_dir),
            check=True,
            shell=True if os.name == 'nt' else False
        )
        print(f"{Colors.GREEN}[Frontend]{Colors.ENDC} Dependencies OK [OK]")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}[Frontend]{Colors.ENDC} Failed to install packages: {e}")
        return False
    return True

def install_playwright():
    """Ensure Playwright browsers are installed."""
    print(f"{Colors.BLUE}[Backend]{Colors.ENDC} Checking Playwright browsers...")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True
        )
        print(f"{Colors.GREEN}[Backend]{Colors.ENDC} Playwright browsers ready [OK]")
    except subprocess.CalledProcessError:
        print(f"{Colors.WARNING}[Backend]{Colors.ENDC} Could not install Playwright browsers (may already be installed)")
    return True

def find_free_port(start=8000, max_tries=5):
    """Find first available port."""
    import socket
    for i in range(max_tries):
        port = start + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return start

def start_backend():
    """Start the FastAPI backend server (tries ports 8000-8004 if busy)."""
    backend_dir = Path(__file__).parent / "backend"
    port = find_free_port(8000)
    
    print(f"{Colors.BLUE}[Backend]{Colors.ENDC} Starting FastAPI on http://localhost:{port}")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload"
    ]
    
    process = subprocess.Popen(
        cmd,
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return process, port

def start_frontend(backend_port=8000):
    """Start the Vite frontend dev server."""
    frontend_dir = Path(__file__).parent / "frontend"
    env = os.environ.copy()
    env["VITE_API_PORT"] = str(backend_port)
    
    print(f"{Colors.CYAN}[Frontend]{Colors.ENDC} Starting Vite (API -> localhost:{backend_port})")
    
    cmd = ["npm", "run", "dev"]
    
    process = subprocess.Popen(
        cmd,
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True if os.name == 'nt' else False,
        env=env
    )
    
    return process

def stream_output(process, prefix, color):
    """Stream process output with prefix."""
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(f"{color}[{prefix}]{Colors.ENDC} {line.rstrip()}")

def main():
    parser = argparse.ArgumentParser(description="Renova Parse CRM Launcher")
    parser.add_argument("--backend", action="store_true", help="Start only backend")
    parser.add_argument("--frontend", action="store_true", help="Start only frontend")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation")
    args = parser.parse_args()
    
    # Default to both if neither specified
    start_both = not args.backend and not args.frontend
    
    print_banner()
    
    # Check requirements
    errors = check_requirements()
    if errors:
        print(f"{Colors.FAIL}Requirements check failed:{Colors.ENDC}")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    # Install dependencies
    if not args.skip_install:
        if args.backend or start_both:
            if not install_backend_deps():
                sys.exit(1)
            install_playwright()
        
        if args.frontend or start_both:
            if not install_frontend_deps():
                sys.exit(1)
    
    processes = []
    backend_port = 8000
    
    try:
        # Start servers
        if args.backend or start_both:
            backend_process, backend_port = start_backend()
            processes.append(("Backend", backend_process, Colors.BLUE))
        
        if args.frontend or start_both:
            frontend_process = start_frontend(backend_port)
            processes.append(("Frontend", frontend_process, Colors.CYAN))
        
        print()
        print(f"{Colors.GREEN}{Colors.BOLD}======================================================{Colors.ENDC}")
        print(f"{Colors.GREEN}  Application is starting...{Colors.ENDC}")
        print()
        if args.backend or start_both:
            print(f"  {Colors.BLUE}Backend API:{Colors.ENDC}  http://localhost:{backend_port}")
            print(f"  {Colors.BLUE}API Docs:{Colors.ENDC}     http://localhost:{backend_port}/docs")
        if args.frontend or start_both:
            print(f"  {Colors.CYAN}Frontend:{Colors.ENDC}     http://localhost:5173 (or 5174 if 5173 busy)")
        print()
        print(f"  Press {Colors.WARNING}Ctrl+C{Colors.ENDC} to stop all servers")
        print(f"{Colors.GREEN}{Colors.BOLD}======================================================{Colors.ENDC}")
        print()
        
        # Stream output from all processes
        import threading
        threads = []
        for name, process, color in processes:
            thread = threading.Thread(
                target=stream_output,
                args=(process, name, color),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # Wait for processes
        exited = set()
        while True:
            for name, process, _ in processes:
                if process.poll() is not None and name not in exited:
                    exited.add(name)
                    print(f"{Colors.WARNING}[{name}]{Colors.ENDC} Process exited with code {process.returncode}")
            if len(exited) == len(processes):
                err = any(p.poll() is not None and p.returncode != 0 for _, p, _ in processes)
                sys.exit(1 if err else 0)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Shutting down...{Colors.ENDC}")
        for name, process, _ in processes:
            print(f"  Stopping {name}...")
            if os.name == 'nt':
                process.terminate()
            else:
                process.send_signal(signal.SIGTERM)
        
        # Wait for processes to terminate
        for name, process, _ in processes:
            process.wait(timeout=5)
        
        print(f"{Colors.GREEN}All servers stopped.{Colors.ENDC}")
        sys.exit(0)

if __name__ == "__main__":
    main()
