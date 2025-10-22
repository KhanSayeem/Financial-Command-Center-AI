#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SHOULD_PAUSE=0
if [[ -t 1 && -z "${FCC_BOOTSTRAP_NO_PAUSE:-}" ]]; then
  SHOULD_PAUSE=1
fi

ensure_logfile() {
  local base cache_dir
  if [[ -n "${FCC_BOOTSTRAP_LOG:-}" ]]; then
    LOG_FILE="$FCC_BOOTSTRAP_LOG"
    mkdir -p "$(dirname "$LOG_FILE")"
    return 0
  fi

  base="${XDG_CACHE_HOME:-}"
  if [[ -z "$base" ]]; then
    base="${HOME:-}"
    if [[ -n "$base" ]]; then
      cache_dir="$base/.cache"
    else
      cache_dir="/tmp"
    fi
  else
    cache_dir="$base"
  fi

  LOG_DIR="$cache_dir/financial-command-center"
  if ! mkdir -p "$LOG_DIR"; then
    LOG_DIR="/tmp/financial-command-center"
    mkdir -p "$LOG_DIR"
  fi

  LOG_FILE="$LOG_DIR/bootstrap-$(date +%Y%m%d-%H%M%S).log"
  export FCC_BOOTSTRAP_LOG="$LOG_FILE"
}

finish() {
  local status=$?
  trap - EXIT
  echo
  if [[ $status -eq 0 ]]; then
    echo "Bootstrap completed successfully."
  else
    echo "Bootstrap failed (exit code $status)."
  fi
  echo "Log file: $LOG_FILE"
  if (( SHOULD_PAUSE )); then
    read -r -p "Press Enter to close this window..." _
  fi
  exit "$status"
}

ensure_logfile
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1
trap finish EXIT

echo "Transcript started. Log file: $LOG_FILE"
echo "Working directory: $REPO_ROOT"

SKIP_TRUST=0
if [[ "$(id -u)" -ne 0 ]]; then
  if [[ -z "${FCC_BOOTSTRAP_ATTEMPTED_SUDO:-}" ]]; then
    if command -v sudo >/dev/null 2>&1; then
      export FCC_BOOTSTRAP_ATTEMPTED_SUDO=1
      echo "Attempting to elevate privileges via sudo..."
      if sudo --preserve-env=FCC_BOOTSTRAP_LOG,FCC_BOOTSTRAP_ATTEMPTED_SUDO "$0" "$@"; then
        exit 0
      fi
      echo "Warning: sudo elevation failed or was cancelled; continuing without administrative privileges."
    else
      echo "Warning: sudo is not available; continuing without administrative privileges."
    fi
  fi
  SKIP_TRUST=1
else
  echo "Running with administrative privileges."
fi

ensure_python() {
  local candidates=() candidate resolved version_check

  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    candidates+=("$REPO_ROOT/.venv/bin/python")
  fi
  if command -v python3 >/dev/null 2>&1; then
    candidates+=("$(command -v python3)")
  fi
  if command -v python >/dev/null 2>&1; then
    candidates+=("$(command -v python)")
  fi

  local unique=()
  for candidate in "${candidates[@]}"; do
    [[ -z "$candidate" ]] && continue
    resolved="$candidate"
    if [[ ! " ${unique[*]} " =~ " $resolved " ]]; then
      unique+=("$resolved")
    fi
  done

  for candidate in "${unique[@]}"; do
    if [[ ! -x "$candidate" ]]; then
      continue
    fi
    if "$candidate" -c 'import sys; exit(0 if sys.version_info[:2] >= (3, 11) else 1)' >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      return 0
    fi
  done

  return 1
}

print_python_guidance() {
  local os distro_hint
  echo
  echo "Python 3.11 or newer is required but was not found on this system."
  os="$(uname -s)"
  case "$os" in
    Darwin)
      echo
      echo "Options for macOS:"
      if command -v brew >/dev/null 2>&1; then
        echo "  • Install via Homebrew:"
        echo "      brew install python@3.11"
      fi
      echo "  • Or download the official installer:"
      echo "      https://www.python.org/downloads/macos/"
      ;;
    Linux)
      echo
      echo "Install Python 3.11 with your package manager, e.g.:"
      if command -v apt-get >/dev/null 2>&1; then
        echo "  • Debian/Ubuntu:"
        echo "      sudo apt-get update && sudo apt-get install python3.11 python3.11-venv"
      elif command -v dnf >/dev/null 2>&1; then
        echo "  • Fedora:"
        echo "      sudo dnf install python3.11 python3.11-pip python3.11-devel"
      elif command -v yum >/dev/null 2>&1; then
        echo "  • RHEL/CentOS:"
        echo "      sudo yum install python3.11 python3.11-pip python3.11-devel"
      elif command -v zypper >/dev/null 2>&1; then
        echo "  • openSUSE:"
        echo "      sudo zypper install python311 python311-pip"
      elif command -v pacman >/dev/null 2>&1; then
        echo "  • Arch Linux:"
        echo "      sudo pacman -S python"
      else
        echo "  • Use your distribution's package manager to install python3.11."
      fi
      echo "If packages are unavailable, download from https://www.python.org/downloads/source/"
      ;;
    *)
      echo
      echo "Please install Python 3.11 or newer from https://www.python.org/downloads/"
      ;;
  esac
  echo
  echo "After installing Python, rerun this script."
}

if ! ensure_python; then
  print_python_guidance
  exit 1
fi

echo "Using Python interpreter: $PYTHON_BIN"

if [[ "$SKIP_TRUST" -eq 1 ]]; then
  echo "Note: running without administrative privileges. Certificate trust will require manual steps."
  echo "  � Recommended: rerun this installer with sudo so the HTTPS certificate is trusted automatically."
  echo "  � Alternatively import "$REPO_ROOT/certs/ca.crt" into your OS trust store manually (see log)."
  echo "Until the certificate authority is trusted your browser will show a security warning when accessing FCC."
fi

cd "$REPO_ROOT"

ARGS=(-m bootstrap install --no-launch)
if [[ "$SKIP_TRUST" -eq 1 ]]; then
  ARGS+=("--skip-trust")
fi

set +e
"$PYTHON_BIN" "${ARGS[@]}"
status=$?
set -e

exit "$status"
