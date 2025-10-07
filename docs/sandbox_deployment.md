# Sandbox & GCP Deployment Playbook

This guide explains how to run the trading bot in a controlled paper-trading
sandbox, then promote the exact same artefact into Google Cloud Platform (GCP)
services without drifting from DRY principles.

> ⚠️ **Live trading is intentionally disabled by default.** You must opt-in by
> setting `TRADING_ENABLE_EXECUTION=1` and providing production Alpaca
> credentials. Keep paper trading on until integration tests and manual sanity
> checks are green.

## 1. Local sandbox execution

1. Copy `AUTH/authAlpaca.example.txt` (or request the template) to
   `AUTH/authAlpaca.txt` and populate your paper trading keys. Keep the file out
   of version control.
2. Create a `.env` in the project root:

   ```dotenv
   TRADING_RUNTIME_ENV=sandbox
   TRADING_ENABLE_EXECUTION=0
   APCA_API_KEY_ID=your-paper-key
   APCA_API_SECRET_KEY=your-paper-secret
   ```

3. Install dependencies and run the bot in read-only mode:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```

4. Inspect the logs; the startup banner now prints the runtime environment and a
   reminder that order execution is disabled.

## 2. Harden for real trading

- Keep credentials in a dedicated secret manager (e.g. GCP Secret Manager) and
  mount them at runtime. Never ship them inside container images.
- Introduce end-to-end tests that verify order submission against Alpaca's
  paper endpoint. Use feature flags to mock responses in CI to avoid rate
  limits.
- Implement health checks in FastAPI or Flask services that validate account
  connectivity before the trading loop starts.

## 3. GCP sandbox deployment

1. **Build once** and reuse the same container image across stages:

   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/alpaca-bot:latest
   ```

2. **Provision Cloud SQL (optional)** for persistent state. Store the connection
   string in Secret Manager and expose it via environment variables; do not
   hardcode DSNs.

3. **Deploy to Cloud Run** in paper mode:

   ```bash
   gcloud run deploy alpaca-sandbox \
     --image gcr.io/PROJECT_ID/alpaca-bot:latest \
     --region=us-central1 \
     --set-env-vars TRADING_RUNTIME_ENV=sandbox,TRADING_ENABLE_EXECUTION=0 \
     --set-secrets APCA_API_KEY_ID=alpaca-paper-key:latest,APCA_API_SECRET_KEY=alpaca-paper-secret:latest \
     --max-instances=1
   ```

4. Use Cloud Scheduler to hit a dedicated `/health` endpoint every minute and
   publish alerts to Cloud Monitoring when connectivity issues surface.

5. Mirror the runtime configuration to a `staging` service before flipping
   `TRADING_ENABLE_EXECUTION` to `1` in production. Review Cloud Audit Logs to
   guarantee only intended principals can mutate deployment variables.

## 4. Recommended next steps

- Break the monolithic `unified_trading_service_with_frontend.py` into
  dedicated FastAPI routers so Cloud Run cold starts stay small and your team
  can deploy UI and trading logic independently.
- Add contract tests for `config.service_settings.get_service_settings()` to
  ensure future refactors keep environment mappings intact.
- Introduce Terraform modules or Google Cloud Deploy pipelines so environment
  promotion is declarative and reviewable instead of click-ops.

