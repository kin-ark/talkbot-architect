"""Shared pytest fixtures for wiz-modifier tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SKILL_DIR.parents[2]
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_DIR = Path(__file__).parent / "golden"
BASELINE_JSON = FIXTURES_DIR / "speech4010869963530658988.json"
BASELINE_WAV = FIXTURES_DIR / "01735200078309635328.wav"


@pytest.fixture
def baseline_json_path() -> Path:
    return BASELINE_JSON


@pytest.fixture
def baseline_dict() -> dict:
    """Fresh parse of the real Empty+Dialogue export (mutable)."""
    return json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
