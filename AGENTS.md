# Repository Guidelines

## Project Structure & Module Organization
- `main.py` drives the live scalping loop; cross-cutting services sit in `core/`, strategy logic in `strategies/`, shared helpers in `utils/`, and runtime settings in `config/` (`unified_config.yml`).
- The Flask layer under `app/` exposes dashboards and APIs via blueprints, while `backend/api/` hosts auxiliary endpoints and `frontend/` supplies static dashboard assets.
- Automated tests are separated into `tests/functional`, `tests/integration`, and `tests/e2e`; browser artefacts land in `playwright-report/` and HTML summaries in `test-reports/`.

## Build, Test, and Development Commands
- Bootstrap Python tooling with `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Start the trading bot with `python main.py`; spin up the Flask dashboard using `python run_flask_app.py` or `./start_flask.sh`.
- Install UI dependencies once via `npm install`, then run Playwright suites with `npm test` or `npm run test:headed`.
- Execute backend checks with `pytest tests/functional -m "not paper_trading"`; the menu-driven `./run_crypto_tests.sh` walks through broader scenarios when needed.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, snake_case modules and functions, PascalCase classes, UPPER_CASE constants, and type hints mirroring current modules.
- Reuse `utils/logging_config.setup_logging()` for log wiring and `core.service_registry` for dependency access instead of ad-hoc globals.
- Keep configuration defaults in YAML and JSON templates; do not commit live credentials or endpoint overrides.

## Testing Guidelines
- Pytest picks up files matching `test_*.py`, classes `Test*`, functions `test_*` (see `pytest.ini`); apply markers (`unit`, `integration`, `slow`, `paper_trading`) to isolate heavy paths.
- Target coverage when touching trading rules: `pytest tests/functional --cov=app --cov=strategies --cov=config`.
- Maintain Playwright flows in `tests/e2e/`; sync selector changes with `frontend/` updates and regenerate visual reports via `npm run test:report`.

## Commit & Pull Request Guidelines
- Use the conventional prefixes seen in history (`feat:`, `fix:`, `docs:`, `chore:`) with imperative subjects under 72 characters.
- PRs should state the intent, list the commands you ran (`pytest …`, `npm test`, `./run_crypto_tests.sh`), and call out config or feature flag impacts.
- Link related issues, include UI screenshots or logs for user-facing changes, and flag reviewers if `paper_trading` paths were exercised.

## Security & Configuration Tips
- Store Alpaca keys and secrets in `AUTH/` or environment variables; keep those files out of version control.
- Validate sandbox versus live credentials before deploying; favour paper trading until functional and integration suites pass.
- Document any new environment variables or auth templates so other contributors can reproduce your setup safely.
