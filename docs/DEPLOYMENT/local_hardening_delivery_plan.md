# Local Deployment Hardening Plan

This document sequences the implementation work required to make the crypto scalping stack production-ready on a single workstation or self-hosted server. Every deliverable is expected to read configuration exclusively from shared environment variables (documented in `.env.example`) and propagate those values into `config/unified_config.yml` or dedicated YAML templates. Avoid in-file constants; if a service needs a new toggle, add it to the shared `.env` contract first.

## 1. Compose-Centric Runtime Architecture

| Profile | Services | Notes |
|---------|----------|-------|
| `core` | `unified-trading-service`, `redis`, `postgres`, `prometheus` | Mount `${LOCAL_DATA_ROOT}` for database volumes; load `env_file: .env` for every service. |
| `analytics` | `grafana`, `risk-api`, `risk-worker` | Grafana provisioning points to `${GRAFANA_PROVISIONING_PATH}`; risk services share the SQLAlchemy DSN from `.env`. |
| `ml` | `signal-gateway`, `sentiment-worker`, optional `jupyter` | Only start when `${ML_PROFILE_ENABLED}` is true to keep resource usage low. |

**Implementation Tasks**
- Create `deploy/local/docker-compose.yml` with the profiles above, ensuring all container-level environment variables derive from the `.env` file or `.env.local` overrides.
- Add Make targets or scripts (`scripts/compose_up.sh`, `scripts/compose_down.sh`) that wrap `docker compose --profile` invocations while surfacing required variables (`LOCAL_SERVICES_ENABLED`, `ML_PROFILE_ENABLED`).
- Document volume expectations in `docs/local_runtime.md` so contributors do not rely on implicit Docker defaults.

**Acceptance Criteria**
- `docker compose --profile core up -d` brings up Redis/Postgres/Prometheus and the trading API with no hard-coded credentials.
- Stopping and restarting the stack preserves database state inside `${LOCAL_DATA_ROOT}`.

## 2. Configuration Contract & Secrets Hygiene

1. **Centralise directories**
   - Use `${LOCAL_DATA_ROOT}` for all local persistence (`postgres`, `redis`, `backtests`).
   - Persist Prometheus and Grafana configuration paths in `${PROMETHEUS_CONFIG_PATH}` and `${GRAFANA_PROVISIONING_PATH}` to keep Docker Compose definitions DRY.

2. **Secrets management**
   - Maintain sanitized credential templates under `AUTH/` and validate them with a pre-commit hook (e.g., `detect-secrets scan`).
   - Add a `scripts/check_env.py` utility that validates required environment variables before Compose startup; fail fast if critical keys are missing.

3. **Configuration propagation**
   - Ensure `config/unified_config.yml` pulls defaults from environment variables using `python-dotenv` in development and `os.environ` in production so both CLI and ASGI entrypoints share identical settings.

## 3. Implementation Backlog by Phase

### Phase 1 – Resilience & Performance
- **WebSocket heartbeat & retry helpers** in `utils/websocket.py` with Prometheus counters (`ws_reconnect_total`, `ws_latency_seconds`). Guard thresholds via `WS_MAX_RECONNECT_ATTEMPTS` and `WS_RETRY_BACKOFF_SECONDS`.
- **Redis caching wrapper** under `utils/cache.py` that respects `REDIS_URL` and `REDIS_TLS_ENABLED`; expose async and sync APIs to reuse across services.
- **SQLAlchemy connection pooling** updates in `database/__init__.py`, using `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` and ensuring tests run against a temporary DSN when `PYTEST_CURRENT_TEST` is set.

### Phase 2 – Local Runtime & Ops
- **Supervisor script** (`scripts/supervise.py`) that reads `LOCAL_HEALTHCHECK_PORT` and `PROCESS_RESTART_BACKOFF_SECONDS`, restarting failed processes and emitting structured JSON logs.
- **Health endpoints** in each service (FastAPI routers under `services/`) returning aggregated status (`redis`, `postgres`, `alpaca`), with toggles set by `LOCAL_SERVICES_ENABLED`.
- **Docker Compose profiles** validated through integration tests that boot the `core` profile before executing `pytest tests/integration`.

### Phase 3 – Trading Controls
- **Strategy registry** stored in PostgreSQL with migrations authored via Alembic (`scripts/migrate.py`). Defaults seeded from `ENABLED_STRATEGIES` and `DEFAULT_POSITION_SIZE_BPS`.
- **OCO order support** implemented inside `strategies/oco.py`, flagged via `OCO_ENABLED` to keep production opt-in.
- **Indicator configuration UI** updates in `frontend-shadcn/` to respect `FRONTEND_INDICATOR_EDITING_ENABLED`, persisting drafts to the API only when the toggle is true.

### Phase 4 – Risk & Analytics
- **Risk analytics workers** inside `risk_management/` reading `RISK_LOOKBACK_DAYS`, `RISK_CONFIDENCE_INTERVAL`, and writing metrics to Redis/Postgres.
- **Versioned Risk API** (`services/risk_api.py`) exposing schemas under `docs/openapi/risk-api.yaml`, rate limited via `RISK_API_RATE_LIMIT_PER_MINUTE`.

### Phase 5 – ML & Signals (Optional)
- **Model server** wrappers that watch `${ML_MODEL_ENDPOINT}` for remote inference and fall back to local models stored under `${LOCAL_DATA_ROOT}/models`.
- **Sentiment ingestion cron** scheduled via APScheduler, controlled by `SENTIMENT_POLL_INTERVAL_SECONDS` and `SENTIMENT_SIGNAL_WEIGHT`.

### Phase 6 – Testing & Automation
- **Integration test harness** that spins up Docker services with `INTEGRATION_TEST_SERVICES` before executing tests.
- **Observability tests** verifying Prometheus scrapes using `PROMETHEUS_EXPORTER_PORT` and ensuring Grafana dashboards load from `${GRAFANA_PROVISIONING_PATH}`.
- **Pre-commit pipeline** mirroring CI: `ruff`, `mypy`, `pytest`, `npm test`, and `detect-secrets`. Document command usage in `docs/TESTING/automation.md`.

## 4. Documentation & Onboarding
- Update `docs/local_runtime.md` with Compose commands, required `.env` keys, and troubleshooting tips (e.g., port collisions).
- Provide example Grafana dashboards and Prometheus scrape configs stored under `config/observability/` so onboarding requires zero manual clicks.
- Keep change logs in `docs/SYSTEM_STATUS_REPORT.md` to reflect new services and metrics, ensuring stakeholders know when toggles are available.

## 5. Pushback & Recommendations
- Do **not** enable ML or sentiment services until Phases 1–2 pass integration and soak testing; otherwise, debugging becomes intractable on local machines.
- Resist duplicating environment variables across service-specific `.env` files. All runtime toggles should live in the root `.env` and be injected via Compose or `dotenv`.
- When adding new services, author smoke tests first. A failing `pytest tests/integration` run should block merges to prevent configuration drift.
- Prioritise metrics parity with production ambitions—if a signal or worker is important enough to run, it needs Prometheus/Grafana coverage from day one.

By following this plan we keep the stack cloud-agnostic, reproducible, and aligned with DRY configuration principles while still leaving room to map the exact same containers onto managed platforms if requirements change later.
