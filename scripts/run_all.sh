#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo "Virtual environment not found. Create it with 'python3 -m venv .venv' before running this script." >&2
  exit 1
fi

source .venv/bin/activate

export TRADING_RUNTIME_ENV=${TRADING_RUNTIME_ENV:-paper}
export TRADING_ENABLE_EXECUTION=${TRADING_ENABLE_EXECUTION:-1}
export ALPACA_AUTH_FILE=${ALPACA_AUTH_FILE:-AUTH/authAlpaca.txt}
export PROMETHEUS_EXPORTER_PORT=${PROMETHEUS_EXPORTER_PORT:-9465}
export UI_PORT=${UI_PORT:-8080}
export API_PORT=${API_PORT:-5001}

PORTS_TO_FREE="${UI_PORT} ${PROMETHEUS_EXPORTER_PORT} ${API_PORT}"

for port in ${PORTS_TO_FREE}; do
  if lsof -ti TCP:${port} >/dev/null; then
    echo "Port ${port} in use; terminating existing process..."
    lsof -ti TCP:${port} | xargs kill -9
  fi
done

command -v honcho >/dev/null 2>&1 || {
  echo "Honcho is required but not installed in this venv. Installing..." >&2
  pip install honcho
}

honcho start bot api ui
