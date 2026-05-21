"""Shared pytest fixtures and helpers for wiz-builder tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_DIR = Path(__file__).parent / "golden"
TEMPLATE_PATH = SKILL_DIR / "templates" / "empty_dialogue.json"


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
def template_dict():
    """Return a fresh parse of the Empty+Dialogue template (mutable copy)."""
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def template_path():
    """Path to the Empty+Dialogue template snapshot."""
    return TEMPLATE_PATH
