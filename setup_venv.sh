#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

uv sync --extra dev

echo ""
echo "Done. Activate with: source .venv/bin/activate"
echo "Run tool:            ./ha_cal.py --help"
