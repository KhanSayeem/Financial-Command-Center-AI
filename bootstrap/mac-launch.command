#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"
if [[ ! -x "./bootstrap/run_unix.sh" ]]; then
  echo "Error: bootstrap/run_unix.sh not found." >&2
  exit 1
fi
exec ./bootstrap/run_unix.sh launch
