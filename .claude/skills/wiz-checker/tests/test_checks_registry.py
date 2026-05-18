"""Tests for the check registry."""

from __future__ import annotations

import pytest
from wizcheck.checks import REGISTRY, get_check, run_all_checks
from wizcheck.ir import FlowGraph, WizFile


@pytest.fixture
def empty_wizfile() -> WizFile:
    return WizFile(
        raw={},
        components={},
        variables={},
        intents={},
        utterances=(),
        audios={},
        flow=FlowGraph(),
    )


def test_registry_lists_four_checks():
    assert set(REGISTRY.keys()) == {"schema", "graph", "variables", "intents"}


def test_get_check_by_name():
    chk = get_check("schema")
    assert callable(chk)


def test_get_check_unknown_raises():
    with pytest.raises(KeyError):
        get_check("nope")


def test_run_all_checks_returns_findings_list(empty_wizfile):
    findings = run_all_checks(empty_wizfile)
    assert isinstance(findings, list)
