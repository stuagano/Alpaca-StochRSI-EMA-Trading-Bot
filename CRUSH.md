# CRUSH.md

This file provides guidelines and commands for agentic coding agents working in this repository.

## Build/Lint/Test Commands

- **Install Dependencies:** `pip install -r requirements.txt`
- **Run all tests:** `pytest`
- **Run a single test file:** `pytest <path_to_test_file>` (e.g., `pytest test_signals.py`)
- **Run a specific test within a file:** `pytest <path_to_test_file>::<test_function_name>`
- **Linting:** (No specific linter configured, assume `flake8` or `pylint` if installed. If not, use standard Python style.)

## Code Style Guidelines

- **Imports:** Group standard library imports, third-party imports, and local imports.
- **Formatting:** Adhere to PEP 8. Use `black` for auto-formatting if available (run `black .`).
- **Types:** Use type hints for function arguments and return values where applicable.
- **Naming Conventions:**
    - `snake_case` for functions, variables, and file names.
    - `PascalCase` for classes.
    - `UPPER_SNAKE_CASE` for constants.
- **Error Handling:** Use `try-except` blocks for anticipated errors. Log errors appropriately.
- **Docstrings:** Use Google-style docstrings for functions and classes.
