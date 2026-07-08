"""Test maturity gate in _as_proposal and fix-loop integration."""
import agents
import samples
from tools import registry


def test_as_proposal_matures_and_reports():
    """Verify _as_proposal calls ensure_mature and adds maturity report to proposal."""
    # Build a simple bot using propose_build (the CLI path)
    built = agents.propose_build(samples.load_manifest("greeting_faq"))
    assert built["ok"], f"Build failed: {built.get('error')}"

    # Shape a proposal dict as propose_build/propose_mods would return
    p = {
        "ok": True,
        "proposed_data": built["proposed_data"],
        "diff": "(test diff)",
        "checker_delta": {},
    }

    # Call _as_proposal — the single choke point
    out = registry._as_proposal(p)

    # Verify structure
    assert out["proposal"] is not None, "Expected proposal to be generated"
    proposal = out["proposal"]

    # Check maturity key is present with correct shape
    assert "maturity" in proposal, "Expected 'maturity' key in proposal"
    maturity = proposal["maturity"]

    # Verify maturity report has required keys
    assert set(maturity.keys()) >= {"auto_fixed", "residual_blockers", "errors"}, \
        f"Maturity report missing required keys. Got: {set(maturity.keys())}"

    # Verify types
    assert isinstance(maturity["auto_fixed"], list), "auto_fixed should be a list"
    assert isinstance(maturity["residual_blockers"], list), "residual_blockers should be a list"
    assert isinstance(maturity["errors"], list), "errors should be a list"

    # Verify findings reflect the matured data
    assert "findings" in proposal, "Expected findings in proposal"
    findings = proposal["findings"]
    assert isinstance(findings, list), "findings should be a list"

    # Verify proposed_data is the matured version
    assert "proposed_data" in proposal, "Expected proposed_data in proposal"
    assert proposal["proposed_data"] is not None, "proposed_data should not be None"


def test_as_proposal_matures_preserves_existing_keys():
    """Verify _as_proposal preserves diff, checker_delta, etc. while adding maturity."""
    built = agents.propose_build(samples.load_manifest("greeting_faq"))
    assert built["ok"]

    p = {
        "ok": True,
        "proposed_data": built["proposed_data"],
        "diff": "(test diff)",
        "checker_delta": {"error_delta": -1},
        "proposed_summary": {"components": []},
        "change_set": {},
        "change_summary": "(summary)",
    }

    out = registry._as_proposal(p)
    proposal = out["proposal"]

    # Verify existing keys are preserved
    assert proposal["diff"] == "(test diff)", "diff should be preserved"
    assert proposal["checker_delta"] == {"error_delta": -1}, "checker_delta should be preserved"
    assert "proposed_summary" in proposal, "proposed_summary should be present"
    assert "change_set" in proposal, "change_set should be present"
    assert "change_summary" in proposal, "change_summary should be present"

    # And maturity is added
    assert "maturity" in proposal, "maturity should be added"


def test_as_proposal_fails_on_error_proposal():
    """Verify _as_proposal handles failed proposals (ok=False)."""
    p = {
        "ok": False,
        "error": "Test error",
    }

    out = registry._as_proposal(p)

    # Should return error, no proposal
    assert out["proposal"] is None, "proposal should be None on error"
    assert out["result"]["ok"] is False, "result.ok should be False"
    assert "error" in out["result"], "result should have error"
    assert out["result"]["error"] == "Test error"
