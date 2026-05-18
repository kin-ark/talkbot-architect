"""Shared pytest fixtures and helpers for wiz-checker tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_path():
    """Return a fixture file path by name."""

    def _path(name: str) -> Path:
        p = FIXTURES_DIR / name
        if not p.exists():
            raise FileNotFoundError(f"Fixture not found: {p}")
        return p

    return _path


@pytest.fixture
def load_fixture(fixture_path):
    """Load a fixture file and return parsed JSON."""

    def _load(name: str) -> dict:
        return json.loads(fixture_path(name).read_text(encoding="utf-8"))

    return _load
