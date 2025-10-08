#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env}"

log() {
  printf '[fix-validation] %s\n' "$1"
}

split_args() {
  local value="$1"
  local -n target_ref="$2"
  target_ref=()
  if [[ -n "$value" ]]; then
    # shellcheck disable=SC2206
    target_ref=($value)
  fi
}

if [[ -f "$ENV_FILE" ]]; then
  log "Loading environment variables from ${ENV_FILE}"
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
else
  log "No env file found at ${ENV_FILE}; proceeding with current environment"
fi

PYTEST_ARGS_DEFAULT="tests/functional -m not\ paper_trading"
PYTEST_ARGS_STRING="${PYTEST_ARGS:-$PYTEST_ARGS_DEFAULT}"
COVERAGE_ARGS_STRING="${COVERAGE_ARGS:---cov=app --cov=strategies --cov=config}"
PLAYWRIGHT_ARGS_STRING="${PLAYWRIGHT_ARGS:-}";
RUN_PLAYWRIGHT_FLAG="${RUN_PLAYWRIGHT:-0}"
RUN_COVERAGE_FLAG="${RUN_COVERAGE:-0}"

split_args "$PYTEST_ARGS_STRING" PYTEST_ARGS_ARRAY
split_args "$COVERAGE_ARGS_STRING" COVERAGE_ARGS_ARRAY
split_args "$PLAYWRIGHT_ARGS_STRING" PLAYWRIGHT_ARGS_ARRAY

command -v python >/dev/null 2>&1 || { log "python interpreter not found in PATH"; exit 1; }
if [[ "$RUN_PLAYWRIGHT_FLAG" == "1" ]]; then
  command -v npm >/dev/null 2>&1 || { log "npm CLI not found in PATH"; exit 1; }
fi

cleanup() {
  popd >/dev/null || true
}

pushd "$PROJECT_ROOT" >/dev/null
trap cleanup EXIT

if [[ "$RUN_COVERAGE_FLAG" == "1" ]]; then
  log "Running pytest with coverage: ${COVERAGE_ARGS_ARRAY[*]} ${PYTEST_ARGS_ARRAY[*]}"
  python -m pytest "${COVERAGE_ARGS_ARRAY[@]}" "${PYTEST_ARGS_ARRAY[@]}"
else
  log "Running pytest: ${PYTEST_ARGS_ARRAY[*]}"
  python -m pytest "${PYTEST_ARGS_ARRAY[@]}"
fi

if [[ "$RUN_PLAYWRIGHT_FLAG" == "1" ]]; then
  if [[ ${#PLAYWRIGHT_ARGS_ARRAY[@]} -gt 0 ]]; then
    log "Running Playwright suite via npm run test:headed -- ${PLAYWRIGHT_ARGS_ARRAY[*]}"
    npm run test:headed -- "${PLAYWRIGHT_ARGS_ARRAY[@]}"
  else
    log "Running Playwright suite via npm run test:headed"
    npm run test:headed
  fi
fi

trap - EXIT
cleanup
