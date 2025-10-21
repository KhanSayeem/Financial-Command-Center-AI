#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Elevating with sudo..."
  exec sudo "$0" "$@"
fi

cd "$REPO_ROOT"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "Python 3.11+ is required. Install Python and rerun this script." >&2
  exit 1
fi

exec "$PYTHON_BIN" -m bootstrap install --no-launch

