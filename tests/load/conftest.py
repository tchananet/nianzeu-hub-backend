"""Registers the ``load`` marker locally: ``pyproject.toml`` is not in Q02 ownership."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "load: Q02 load run against an authorised test VPS; needs Q02_LOAD_TEST=1",
    )
