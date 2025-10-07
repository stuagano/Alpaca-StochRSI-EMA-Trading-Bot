"""Package configuration for optional dependency extras."""

from __future__ import annotations

from pathlib import Path

from setuptools import setup

from config.runtime_dependencies import strategy_runtime_requirement_specs

STRATEGY_RUNTIME_EXTRAS = tuple(strategy_runtime_requirement_specs())


def _read_readme() -> str:
    readme_path = Path(__file__).resolve().parent / "README.md"
    return readme_path.read_text(encoding="utf-8")


def _setup_package() -> None:
    setup(
        name="alpaca-stochrsi-ema-trading-bot",
        version="0.1.0",
        description="Algorithmic trading bot with Alpaca, StochRSI, and EMA strategies.",
        long_description=_read_readme(),
        long_description_content_type="text/markdown",
        extras_require={"strategy": list(STRATEGY_RUNTIME_EXTRAS)},
        python_requires=">=3.9",
    )


if __name__ == "__main__":
    _setup_package()
