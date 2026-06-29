import orchestrator
from orchestrator import run_turn_stream, _MAX_FIX_BACKSTOPS, _SYSTEM
from llm.base import FakeLLMClient, LLMResponse, ToolCall
from session import Session


def _sess():
    s = Session()
    s.load({"BizSpeechComponent": []})
    return s


def _events(client, session, msg="go"):
    return list(run_turn_stream(client, session, msg))


def _proposal(findings):
    return {"proposed_data": {"BizSpeechComponent": []}, "diff": "+x",
            "checker_delta": {"errors_before": 0, "errors_after": len(findings)},
            "findings": findings}


_ERR = [{"code": "WIZ106", "severity": "error", "id": "n1", "message": "bad route"}]


def test_system_prompt_has_best_practice_and_fix_loop():
    assert "Fix loop" in _SYSTEM
    assert "Unclassified" in _SYSTEM
    assert "never" in _SYSTEM.lower()


def test_backstop_forces_a_fix_then_finishes(monkeypatch):
    # dispatch: 1st tool call → error proposal; 2nd tool call → clean proposal
    calls = {"n": 0}
    def fake_dispatch(name, args, data):
        calls["n"] += 1
        findings = _ERR if calls["n"] == 1 else []
        return {"result": {"ok": True}, "proposal": _proposal(findings)}
    monkeypatch.setattr(orchestrator.registry, "dispatch", fake_dispatch)

    tc = lambda i: ToolCall(id=f"c{i}", name="apply_mods", arguments={})
    client = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[tc(1)]),   # round 1: makes error proposal
        LLMResponse(text="done?", tool_calls=[]),     # round 2: tries to finish (dirty) → backstop
        LLMResponse(text=None, tool_calls=[tc(2)]),   # round 3: fixes → clean proposal
        LLMResponse(text="all set", tool_calls=[]),   # round 4: finish (clean)
    ])
    evs = _events(client, _sess())
    autofix = [e for e in evs if e["type"] == "autofix"]
    done = [e for e in evs if e["type"] == "done"]
    assert len(autofix) == 1 and autofix[0]["count"] == 1
    assert len(done) == 1 and done[0]["canceled"] is False


def test_backstop_caps_and_finishes_dirty(monkeypatch):
    monkeypatch.setattr(orchestrator.registry, "dispatch",
                        lambda name, args, data: {"result": {"ok": True}, "proposal": _proposal(_ERR)})
    tc = ToolCall(id="c", name="apply_mods", arguments={})
    # tool call once (sets the dirty proposal), then keep trying to finish
    client = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[tc]),
        *[LLMResponse(text="finish", tool_calls=[]) for _ in range(6)],
    ])
    evs = _events(client, _sess())
    assert len([e for e in evs if e["type"] == "autofix"]) <= _MAX_FIX_BACKSTOPS
    assert any(e["type"] == "done" for e in evs)


def test_no_proposal_turn_finishes_without_autofix():
    client = FakeLLMClient(script=[LLMResponse(text="hello", tool_calls=[])])
    evs = _events(client, _sess())
    assert not [e for e in evs if e["type"] == "autofix"]
    assert [e for e in evs if e["type"] == "done"]
