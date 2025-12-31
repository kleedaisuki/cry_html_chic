#!/usr/bin/env bash
# Set up Python virtual environment and install the project in editable mode with dev dependencies.
# - Creates a .venv at project root
# - Activates the venv
# - Upgrades pip
# - Installs with: pip install -e ".[dev]"

set -euo pipefail

echo "==> Starting Python environment setup..."

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "==> Checking Python installation..."
python3 --version

if [[ ! -d ".venv" ]]; then
  echo "==> Creating virtual environment (.venv)..."
  python3 -m venv .venv
else
  echo "==> Virtual environment already exists (.venv)"
fi

echo "==> Activating virtual environment..."
# shellcheck disable=SC1091
source ".venv/bin/activate"

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

echo "==> Installing project in editable mode with dev dependencies..."
pip install -e ".[dev]"

echo "==> Environment setup complete."
echo "==> Virtual environment: .venv"
echo "==> You can now run: ingest --help"
