# Local-First Crypto Scalping System Delivery Plan

This roadmap reframes the backlog around a hardened, cloud-agnostic deployment that can run end to end on a developer workstation or a self-hosted server. Every capability is designed to be toggled through shared environment variables and reflected in `config/unified_config.yml`, keeping configuration DRY while avoiding hard dependencies on managed cloud services.

## Guiding Principles
- **Centralised configuration**: extend `.env` coverage and flow values into the unified config loader so features stay switchable without touching code.
- **Containerised local stack**: package Redis, PostgreSQL, Prometheus, Grafana, and supporting workers behind Docker Compose profiles so the entire platform spins up with a single command.
- **Observability by default**: require structured logging, metrics, and health probes for every service; expose them through local Prometheus/Grafana dashboards.
- **Feature gating & safety**: drive user-facing behaviour through feature flags and paper-trading toggles so risky changes never hit live funds prematurely.

## Phase 1 – Platform Resilience & Performance
1. **WebSocket Reliability**
   - Implement heartbeat publishing, exponential backoff, and offline queueing with shared async helpers in `utils/`.
   - Track reconnect attempts and message latency with Prometheus counters scraped locally.
   - Configuration: `WS_HEARTBEAT_INTERVAL_SECONDS`, `WS_MAX_RECONNECT_ATTEMPTS`, `WS_RETRY_BACKOFF_SECONDS`.

2. **Caching & Connection Pooling**
   - Run Redis via Docker Compose and introduce a pooled SQLAlchemy engine for historical queries against a local PostgreSQL instance.
   - Configuration: `REDIS_URL`, `REDIS_TLS_ENABLED`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DATABASE_URL`.

3. **Dashboard Optimisations**
   - Add API pagination and UI virtual scrolling components while surfacing cache hit ratios and API latencies on Grafana.
   - Configuration: `NEXT_PUBLIC_ENABLE_VIRTUAL_SCROLLING`, `NEXT_PUBLIC_DASHBOARD_PAGINATION_SIZE`.

## Phase 2 – Local Runtime & Ops Hardening
1. **Docker Compose Profiles**
   - Define profiles for `core`, `analytics`, and `ml` services so contributors can start only what they need (`docker compose --profile core up`).
   - Configuration: `DOCKER_COMPOSE_DEFAULT_PROFILE`, `LOCAL_SERVICES_ENABLED`.

2. **Secrets & Credential Hygiene**
   - Keep credentials in versioned templates under `AUTH/` and load live values via `.env`/`.env.local`; use direnv or dotenv-linter to enforce completeness.
   - Configuration: `ALPACA_AUTH_FILE`, `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`.

3. **Process Supervision & Health Checks**
   - Add local supervisor scripts (e.g., `scripts/supervise.py`) that restart crashed workers and publish health endpoints consumed by the dashboard.
   - Configuration: `LOCAL_HEALTHCHECK_PORT`, `PROCESS_RESTART_BACKOFF_SECONDS`.

## Phase 3 – Advanced Trading Controls
1. **Strategy Orchestrator & OCO Support**
   - Build a strategy registry under `strategies/` with metadata describing inputs and default toggles persisted to the local PostgreSQL database.
   - Configuration: `ENABLED_STRATEGIES`, `DEFAULT_POSITION_SIZE_BPS`, `OCO_ENABLED`.

2. **Indicator Configuration Tooling**
   - Extend the ShadCN dashboard to edit indicator parameters, storing drafts locally before they are persisted through authenticated APIs.
   - Configuration: `FRONTEND_INDICATOR_EDITING_ENABLED`, `DASHBOARD_SESSION_TIMEOUT_MINUTES`.

3. **Backtesting Enhancements**
   - Run backtests in Dockerised workers pulling data from local CSV/Parquet stores and writing results to `database/` for replay in the dashboard.
   - Configuration: `BACKTEST_DATA_DIR`, `BACKTEST_CONCURRENCY`, `BACKTEST_RETENTION_DAYS`.

## Phase 4 – Risk & Analytics
1. **Portfolio Analytics**
   - Compute VaR, beta, correlation matrices, and Kelly sizing within dedicated `risk_management/` services relying on the local database for inputs.
   - Configuration: `RISK_LOOKBACK_DAYS`, `RISK_CONFIDENCE_INTERVAL`, `KELLY_CAPITAL_FRACTION_CAP`.

2. **Central Risk API**
   - Standardise responses consumed by both trading services and dashboards with versioned schemas checked into `docs/openapi/`.
   - Configuration: `RISK_API_BIND`, `RISK_API_RATE_LIMIT_PER_MINUTE`.

## Phase 5 – ML & Signal Intelligence (Optional Profile)
1. **Model Lifecycle**
   - Package signal models as separate Docker services exposing REST/gRPC endpoints with hot-reloadable weights from `models/`.
   - Configuration: `ML_MODEL_ENDPOINT`, `ML_MODEL_TIMEOUT_SECONDS`, `ML_SIGNAL_THRESHOLD`, `ML_PROFILE_ENABLED`.

2. **Sentiment & Pattern Ingestion**
   - Stream Twitter/Reddit sentiment via locally scheduled jobs that write into the analytics database for downstream scoring.
   - Configuration: `SENTIMENT_SIGNAL_WEIGHT`, `SENTIMENT_POLL_INTERVAL_SECONDS`.

## Phase 6 – Testing, Observability & Automation
1. **Automated Testing**
   - Achieve >80% coverage with `pytest` suites and ensure Playwright flows cover critical dashboard paths.
   - Extend `./run_crypto_tests.sh` to spin up Docker services needed for integration tests automatically.

2. **Observability Stack**
   - Ship structured logs to rotating files in `logs/` and expose metrics via OpenTelemetry exporters consumed by local Prometheus.
   - Configuration: `ENABLE_PROMETHEUS_METRICS`, `PROMETHEUS_EXPORTER_PORT`, `LOCAL_LOG_LEVEL`.

3. **Local CI Hooks**
   - Wire pre-commit hooks for linting, typing, and secrets detection; mirror the pipeline in GitHub Actions using only services bootable via Docker.
   - Configuration: `PRECOMMIT_PROFILES`, `CI_PARALLELISM`.

## Dependencies & Next Actions
- Finalise the configuration contract and ensure `.env.example` covers every toggle referenced above.
- Author Docker Compose profiles and document `make`/script entrypoints for spinning up the stack locally.
- Prioritise Phase 1 resilience work before introducing new strategies or ML services; it unlocks reliable paper trading without cloud support.

## Pushback & Recommendations
Attempting to bolt on advanced analytics or ML before stabilising the local runtime will create operational drag and brittle demos. Harden the baseline services, automate Docker-driven test environments, and prove the `.env` contract before touching optional profiles. Once the local stack is deterministic, we can revisit remote deployment targets without compromising DRY configuration or developer velocity.
