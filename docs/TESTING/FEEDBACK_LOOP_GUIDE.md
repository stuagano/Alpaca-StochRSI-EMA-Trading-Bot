# Closing the Fix-to-Test Feedback Loop

This guide explains how to quickly validate code fixes by turning them into reproducible, automated checks. Follow the steps below whenever you address a bug or regression so you can prove the fix works and prevent future breakage.

## 1. Start With a Failing Scenario
1. **Reproduce the bug** using the smallest possible scenario (CLI command, HTTP request, strategy input, etc.). Capture any log snippets or configuration you need.
2. **Codify the scenario as a test** so it fails before your fix:
   - Prefer `pytest` unit or integration tests for Python modules. When the regression involves the StochRSI strategy or its volume gating, extend the scenarios in `tests/functional/strategies/test_enhanced_stoch_rsi_strategy.py` so the loop exercises confirmation, rejection, and bypass behaviour together.
   - For dashboard/UI regressions, add or extend a Playwright spec under `tests/e2e/`.
   - Use shared fixtures and helpers from `tests/` to stay DRY—do not duplicate mock setups.
3. **Parametrize new tests** when multiple inputs should behave the same. This keeps the suite concise while covering more cases.

## 2. Run Targeted Tests Continuously
1. Use `pytest -k "<pattern>"` or `pytest tests/path/test_file.py::TestClass::test_case` to iterate quickly while the fix is in progress.
2. Enable `pytest --maxfail=1 --lf` to rerun only the last failures until they pass.
3. For Playwright, run `npm run test:headed -- <pattern>` to focus on the affected journey.
4. Keep `.env` values in sync with the templates under `config/` and load them via `python-dotenv` rather than hardcoding credentials in tests.
5. Configure `pytest.ini` markers instead of duplicating skip logic in each test—`@pytest.mark.integration` already exists for long-running paths.

## 3. Automate Verification
1. **Local pre-commit hooks**: configure `pre-commit` to run linting and the relevant `pytest` subsets before you push. Keep the hook list in a shared `.pre-commit-config.yaml` at the repo root; extend that file instead of copy/pasting scripts into `.git/hooks`.
2. **Guided verification script**: run `scripts/run_fix_validation.sh` to execute the minimum viable regression suite and optional UI tests while hydrating environment variables from your `.env`. Set `PYTEST_ARGS`, `RUN_PLAYWRIGHT`, or `RUN_COVERAGE` in the same `.env` to customise behaviour without editing the script. The repo-level `pytest.ini` keeps shared markers (`integration`, `performance`, `paper_trading`, etc.) registered so that ad-hoc invocations match CI.
3. **Cloud automation**:
   - Wire the same commands into your CI/CD provider (GitHub Actions, GitLab CI, Jenkins, etc.) so every push runs the targeted suites. Keep credentials in the platform's secret store and inject them as environment variables at runtime instead of hardcoding values.
   - Configure deployment pipelines to surface failing regression checks immediately—treat a red suite as a release blocker until it is green again.
4. Publish HTML/JSON coverage reports so you can confirm the fix increases coverage for the affected module.

## 4. Prove the Fix in the Runtime Environment
1. If the bug surfaced in live trading, replay the failing market data through the backtesting harness before and after the fix.
2. Capture logs by enabling structured logging via `utils/logging_config.setup_logging()` and ship them to your centralized log aggregator for later auditing. Rotate API keys through `AUTH/` templates or your secret store—avoid sprinkling them through multiple YAML files.
3. Roll the change out to a staging environment first. Use feature flags or configuration toggles in `config/unified_config.yml` instead of inline constants so you can flip behavior without redeploying.

## 5. Document and Share
1. Update the relevant runbook in `docs/` with a short summary of the root cause, the new automated test, and how to rerun it. Link directly to the helper script or Make target you touched so the next engineer avoids re-learning the workflow.
2. Reference the new test name and command in your pull request description so reviewers can reproduce the validation quickly.
3. If the fix adds an environment variable, document it in `config/README.md` (or create one) and provide a `.env.example` update.

## 6. Continuous Improvement Checklist
- [ ] Every bug fix adds at least one failing test first.
- [ ] Tests run locally before commit and again in CI/CD.
- [ ] Secrets stay in `.env` files or Secret Manager—never hardcoded.
- [ ] Coverage reports show the affected module is now exercised.
- [ ] Staging validation and log review happen before production rollout.
- [ ] `scripts/run_fix_validation.sh` (or its CI equivalent) stays the single source of truth for the regression commands.

## 7. Suggested Workflow Template

1. **Create a focused branch** named after the bug ticket (`fix/orders-slip-123`). Document assumptions in the branch description so reviewers can double-check them.
2. **Capture the regression** by writing the failing test first. Reference shared fixtures (`tests/functional/fixtures/`) before introducing new ones.
3. **Tighten the loop** by running:
   ```bash
   ENV_FILE=.env.development \
   PYTEST_ARGS="tests/functional/orders/test_slippage.py::TestSlippage::test_regression" \
   RUN_PLAYWRIGHT=0 \
   scripts/run_fix_validation.sh
   ```
4. **Extend coverage when relevant** by toggling `RUN_COVERAGE=1` in your `.env` once the bug is fixed to ensure the delta is measured.
5. **Update documentation** within the same PR—include the failing test's command and the validation script invocation in your PR checklist to keep reviewers aligned.

Treat any deviation from this workflow as technical debt to be ticketed immediately so the team can resolve it without breaking DRY.

Keeping this loop tight ensures regressions surface immediately, reviewers trust the fix, and production trading stays stable.
