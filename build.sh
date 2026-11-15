#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv"

echo "========================================"
echo "  DevDesk - Build & Validate"
echo "========================================"
echo

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "[ERROR] Python not found. Install Python 3.11+ and try again."
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "[1/4] Creating virtual environment..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[2/4] Upgrading pip..."
python -m pip install --upgrade pip -q

echo "[3/4] Installing dependencies..."
python -m pip install -r requirements.txt -q

echo "[4/4] Running tests and packaging..."
export PYTHONPATH="$(pwd)"
python -m pytest tests/ -q
python scripts/build_package.py --target linux

echo

echo "========================================"
echo "  Build completed successfully"
echo "========================================"
