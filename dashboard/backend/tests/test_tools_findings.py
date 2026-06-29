import agents
from tools.registry import _as_proposal

_BASE_P = {
    "ok": True,
    "proposed_data": {"BizSpeechComponent": []},
    "diff": "+x",
    "checker_delta": {"errors_before": 0, "errors_after": 1},
    "change_summary": "Adds 1 component · ⚠ +1 errors",
}
_ERR = [{"code": "WIZ106", "severity": "error", "entity": "node", "id": "n1",
         "field": "routes", "message": "branch routes to a missing node"}]


def test_findings_surfaced_in_result_and_proposal(monkeypatch):
    monkeypatch.setattr(agents, "validate", lambda d: _ERR)
    out = _as_proposal(dict(_BASE_P))
    assert out["result"]["findings"] == _ERR
    assert out["proposal"]["findings"] == _ERR
    # existing result keys intact
    for k in ("ok", "diff", "checker_delta", "change_summary"):
        assert k in out["result"]


def test_no_findings_key_when_clean(monkeypatch):
    monkeypatch.setattr(agents, "validate", lambda d: [])
    out = _as_proposal(dict(_BASE_P))
    assert "findings" not in out["result"]      # lean result when clean
    assert out["proposal"]["findings"] == []    # proposal still carries the (empty) list


def test_error_passthrough_unchanged(monkeypatch):
    called = []
    monkeypatch.setattr(agents, "validate", lambda d: called.append(d) or [])
    out = _as_proposal({"ok": False, "error": "bad op", "known_ops": ["x"]})
    assert out["proposal"] is None
    assert out["result"]["ok"] is False and out["result"]["error"] == "bad op"
    assert called == []                          # validate not called on the error path
