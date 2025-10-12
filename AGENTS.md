# Repository Guidelines

## Project Structure & Module Organization
- `main.py` orchestrates the live scalping loop; shared services live under `core/` and strategy logic under `strategies/`.
- Flask dashboards and APIs sit in `app/`, auxiliary endpoints in `backend/api/`, and static assets in `frontend/`.
- Shared helpers are in `utils/`, runtime settings (including `unified_config.yml`) belong in `config/`, and Auth templates reside in `AUTH/`.
- Tests are split into `tests/functional`, `tests/integration`, and `tests/e2e`; Playwright output drops into `playwright-report/` and HTML summaries into `test-reports/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` – bootstrap Python tooling.
- `python main.py` – launch the trading bot.
- `python run_flask_app.py` or `./start_flask.sh` – start the dashboard server.
- `pytest tests/functional -m "not paper_trading"` – run core backend checks.
- `npm install` (once) then `npm test` or `npm run test:headed` – install UI deps and execute Playwright suites.
- `./run_crypto_tests.sh` – menu-driven end-to-end scenarios.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, snake_case modules/functions, PascalCase classes, UPPER_CASE constants, and type hints consistent with neighbor modules.
- Reuse `utils/logging_config.setup_logging()` for log wiring and `core.service_registry` for dependency access instead of bespoke globals.
- Keep defaults in YAML/JSON config templates; never hard-code live credentials.

## Testing Guidelines
- Pytest auto-discovers `test_*.py`, `Test*` classes, and `test_*` functions; apply markers (`unit`, `integration`, `slow`, `paper_trading`) to scope runs.
- Target functional coverage with `pytest tests/functional --cov=app --cov=strategies --cov=config`.
- Maintain Playwright flows in `tests/e2e/`; align selector updates with `frontend/` changes and regenerate reports via `npm run test:report`.

## Commit & Pull Request Guidelines
- Use conventional prefixes (`feat:`, `fix:`, `docs:`, `chore:`) with imperative subjects under 72 characters.
- PRs should list executed commands (e.g., `pytest …`, `npm test`, `./run_crypto_tests.sh`), note config or feature flag impacts, and attach logs or UI screenshots for user-facing updates.
- Link related issues and flag reviewers whenever `paper_trading` paths were exercised.

## Security & Configuration Tips
- Store Alpaca keys/secrets in `AUTH/` or environment variables and keep them out of version control.
- Confirm sandbox vs. live credentials before deployment; prefer paper trading until functional/integration suites pass.
- Document new env vars or auth templates so others can reproduce the setup safely.
