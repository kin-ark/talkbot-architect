"""Test the maturity gate: _as_proposal behavior with mature parameter."""
import pytest
import copy
from tools.registry import _as_proposal


@pytest.fixture
def base_proposal():
    """A minimal valid proposal."""
    return {
        "ok": True,
        "proposed_data": {"speechId": "test", "BizSpeechComponent": []},
        "diff": "test change",
        "checker_delta": None,
    }


def test_as_proposal_default_no_mature(base_proposal):
    """_as_proposal(p) with default mature=False: no maturity key, original data."""
    result = _as_proposal(copy.deepcopy(base_proposal))
    assert result["result"]["ok"] is True
    assert "maturity" not in result["proposal"]
    # Data should not be matured (same as input)
    assert result["proposal"]["proposed_data"] == base_proposal["proposed_data"]


def test_as_proposal_mature_true(base_proposal):
    """_as_proposal(p, mature=True): includes maturity key even if empty."""
    result = _as_proposal(copy.deepcopy(base_proposal), mature=True)
    assert result["result"]["ok"] is True
    # maturity key should exist (even if empty lists)
    assert "maturity" in result["proposal"]
    assert isinstance(result["proposal"]["maturity"], dict)
    assert "auto_fixed" in result["proposal"]["maturity"]


def test_as_proposal_error_handling():
    """_as_proposal handles errors gracefully."""
    error_proposal = {"ok": False, "error": "test error"}
    result = _as_proposal(error_proposal)
    assert result["result"]["ok"] is False
    assert result["result"]["error"] == "test error"
    assert result["proposal"] is None


def test_as_proposal_with_findings(base_proposal):
    """_as_proposal includes findings in both result and proposal."""
    result = _as_proposal(copy.deepcopy(base_proposal))
    # Should always validate and include findings
    assert "findings" in result["proposal"]
    # Result should have findings if they exist
    if result["proposal"]["findings"]:
        assert result["result"].get("findings") == result["proposal"]["findings"]
