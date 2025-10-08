# Local Runtime Guide

This guide focuses on running the unified trading service on your workstation so you can verify behaviour against the Alpaca paper-trading API before deploying to remote environments.

## 1. Bootstrap dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install  # if you plan to run the React frontend build or Playwright tests
```

Install the optional dependencies that power the live integrations:

- `alpaca-trade-api` for market data and order routing.
- `python-dotenv` to automatically load the environment variables listed below.

## 2. Configure environment variables

Create a `.env` file in the project root to keep runtime configuration DRY:

```ini
TRADING_RUNTIME_ENV=sandbox
APCA_API_KEY_ID=your-paper-key
APCA_API_SECRET_KEY=your-paper-secret
APCA_API_BASE_URL=https://paper-api.alpaca.markets
ALPACA_AUTH_FILE=AUTH/authAlpaca.txt

# Background worker roster for localhost usage
TRADING_SERVICE_BACKGROUND_WORKERS=update_cache,crypto_scanner,crypto_scalping_trader
```

Adjust the roster to experiment with different combinations of background jobs. When the variable is omitted the service will execute every registered worker. Setting it to an empty string disables all workers, which is helpful when you want to load the UI without touching Alpaca.

## 3. Launch the unified service

```bash
uvicorn unified_trading_service_with_frontend:app --reload --port 9000
```

The lifespan hook now prints the workers that have been activated so you can confirm the localhost runtime matches your `.env` expectations.

If you only want to validate API connectivity without the React bundle, run the Python module directly:

```bash
python unified_trading_service_with_frontend.py
```

## 4. Docker Compose workflow

The repository ships with a Compose stack (`deploy/local/docker-compose.yml`) so you can start Redis, Postgres, Prometheus, Grafana, and the optional ML/risk workers without hand-crafted shell scripts.

1. Review `.env.example` and copy the relevant keys into your `.env`. At a minimum you need to set `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DATABASE_URL`, `REDIS_URL`, `LOCAL_DATA_ROOT`, and the image tags (`POSTGRES_IMAGE`, `REDIS_IMAGE`, `PROMETHEUS_IMAGE`, `GRAFANA_IMAGE`).
2. Bring up the default profiles:

   ```bash
   ./scripts/compose_up.sh            # boots the "core" profile
   ./scripts/compose_up.sh analytics  # adds Grafana + risk services
   ./scripts/compose_up.sh ml         # only works when ML_PROFILE_ENABLED=true
   ```

   The wrapper calls `scripts/check_env.py` to derive container-specific variables (`COMPOSE_DATABASE_URL`, `COMPOSE_REDIS_URL`) from your `.env`, creates `${LOCAL_DATA_ROOT}` subdirectories, and injects them into `docker compose` so every container reads the same configuration contract.

3. Tear everything down with the matching helper:

   ```bash
   ./scripts/compose_down.sh analytics -v
   ```

   The first argument selects profiles, any additional flags are forwarded to `docker compose down` (e.g. `-v` to prune volumes).

Metrics ship with the stack out of the box: `main.py` exposes a Prometheus exporter on `PROMETHEUS_EXPORTER_PORT`, the risk API publishes `/metrics`, and both Prometheus and Grafana mount their config from `config/observability/`. Custom dashboards live under `config/observability/grafana/provisioning/dashboards/` so you can iterate locally without manual UI steps.

## 5. Recommended next steps

- Use `tests/unit/config/test_service_settings.py` to verify configuration parsing.
- Consider running the service inside `poetry run` or `pipenv run` once you migrate dependency management to those tools for consistent environments across teammates.
- When you are ready to move beyond localhost, promote the same container configuration to your sandbox account and reuse the `.env` keys via your preferred secret manager.
