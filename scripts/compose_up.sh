#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
COMPOSE_FILE="${REPO_ROOT}/deploy/local/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "error: docker-compose file not found at ${COMPOSE_FILE}" >&2
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker command not found. Install Docker before continuing." >&2
  exit 1
fi

CHECK_OUTPUT="$(python3 "${REPO_ROOT}/scripts/check_env.py" --env-file "${ENV_FILE}" 2>&1)"
CHECK_STATUS=$?
if [[ ${CHECK_STATUS} -ne 0 ]]; then
  printf '%s\n' "${CHECK_OUTPUT}" >&2
  exit ${CHECK_STATUS}
fi

while IFS= read -r line; do
  case "${line}" in
    COMPOSE_DATABASE_URL=*|COMPOSE_REDIS_URL=*)
      export "${line}"
      ;;
    warning:*)
      printf '%s\n' "${line}" >&2
      ;;
    "") ;;
    *)
      printf '%s\n' "${line}" >&2
      ;;
  esac
done <<< "${CHECK_OUTPUT}"

LOCAL_DATA_ROOT="${LOCAL_DATA_ROOT:-${REPO_ROOT}/.localstack}"
mkdir -p \
  "${LOCAL_DATA_ROOT}" \
  "${LOCAL_DATA_ROOT}/postgres" \
  "${LOCAL_DATA_ROOT}/redis" \
  "${LOCAL_DATA_ROOT}/prometheus" \
  "${LOCAL_DATA_ROOT}/grafana" \
  "${LOCAL_DATA_ROOT}/logs"

REQUESTED_PROFILES="${1:-${LOCAL_SERVICES_ENABLED:-core}}"
IFS=',' read -r -a PROFILE_LIST <<< "${REQUESTED_PROFILES}"

PROFILE_ARGS=()
ML_ENABLED=false
case "${ML_PROFILE_ENABLED:-false}" in
  1|true|TRUE|True|yes|on|ON)
    ML_ENABLED=true
    ;;
  *)
    ML_ENABLED=false
    ;;
 esac

for profile in "${PROFILE_LIST[@]}"; do
  profile_trimmed="${profile//[[:space:]]/}"
  if [[ -z "${profile_trimmed}" ]]; then
    continue
  fi
  if [[ "${profile_trimmed}" == "ml" && "${ML_ENABLED}" != true ]]; then
    echo "warning: skipping ml profile because ML_PROFILE_ENABLED is disabled" >&2
    continue
  fi
  PROFILE_ARGS+=(--profile "${profile_trimmed}")
done

if [[ ${#PROFILE_ARGS[@]} -eq 0 ]]; then
  echo "error: no valid docker compose profiles selected" >&2
  exit 1
fi

docker compose \
  --env-file "${ENV_FILE}" \
  --project-name "${COMPOSE_PROJECT_NAME:-alpaca_scalper}" \
  -f "${COMPOSE_FILE}" \
  "${PROFILE_ARGS[@]}" \
  up -d
