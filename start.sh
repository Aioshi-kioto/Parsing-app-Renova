#!/bin/bash
# Renova Parse CRM - Launcher for macOS and Linux
cd "$(dirname "$0")"
if command -v python3 &>/dev/null; then
  exec python3 start.py "$@"
else
  exec python start.py "$@"
fi
