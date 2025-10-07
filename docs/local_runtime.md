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

## 4. Recommended next steps

- Use `tests/unit/config/test_service_settings.py` to verify configuration parsing.
- Consider running the service inside `poetry run` or `pipenv run` once you migrate dependency management to those tools for consistent environments across teammates.
- When you are ready to move beyond localhost, promote the same container configuration to your sandbox account and reuse the `.env` keys via your preferred secret manager.
