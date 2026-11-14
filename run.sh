#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  DevDesk - Starting..."
echo "========================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found. Install with: sudo apt install python3 python3-venv python3-full"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] Installing / updating dependencies..."
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

echo "[3/3] Launching DevDesk..."
echo
export PYTHONPATH="$(pwd)"
python main.py
