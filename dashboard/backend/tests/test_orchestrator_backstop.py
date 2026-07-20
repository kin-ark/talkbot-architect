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

    def tc(i):
        return ToolCall(id=f"c{i}", name="apply_mods", arguments={})
    client = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[tc(1)]),   # round 1: makes error proposal
        LLMResponse(text="done?", tool_calls=[]),     # round 2: tries to finish (dirty) → backstop
        LLMResponse(text=None, tool_calls=[tc(2)]),   # round 3: fixes → clean proposal
        LLMResponse(text="all set", tool_calls=[]),   # round 4: finish (clean)
    ])
    evs = _events(client, _sess())
    fixing = [e for e in evs if e["type"] == "phase" and e["phase"] == "fixing"]
    done = [e for e in evs if e["type"] == "done"]
    assert len(fixing) == 1 and fixing[0]["errors"] == 1 and fixing[0]["round"] == 1
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
    assert len([e for e in evs if e["type"] == "phase" and e["phase"] == "fixing"]) <= _MAX_FIX_BACKSTOPS
    assert any(e["type"] == "done" for e in evs)


def test_no_proposal_turn_finishes_without_fixing():
    client = FakeLLMClient(script=[LLMResponse(text="hello", tool_calls=[])])
    evs = _events(client, _sess())
    assert not [e for e in evs if e["type"] == "phase" and e["phase"] == "fixing"]
    assert [e for e in evs if e["type"] == "done"]


class _RaisingClient:
    model = "fake"
    def stream_chat(self, messages, tools):
        raise RuntimeError("connection error: provider unreachable")
        yield  # pragma: no cover  (make it a generator)


def test_transient_error_on_llm_exception():
    evs = _events(_RaisingClient(), _sess())
    errs = [e for e in evs if e["type"] == "error"]
    assert errs and errs[0]["kind"] == "transient" and errs[0]["recovery"] == ["retry"]
    assert any(e["type"] == "done" for e in evs)


def test_proposal_blocked_error_after_backstops_exhausted(monkeypatch):
    monkeypatch.setattr(orchestrator.registry, "dispatch",
                        lambda name, args, data: {"result": {"ok": True}, "proposal": _proposal(_ERR)})
    tc = ToolCall(id="c", name="apply_mods", arguments={})
    client = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[tc]),
        *[LLMResponse(text="finish", tool_calls=[]) for _ in range(6)],
    ])
    evs = _events(client, _sess())
    blocked = [e for e in evs if e["type"] == "error" and e["kind"] == "proposal_blocked"]
    assert blocked and blocked[0]["recovery"] == ["fix", "discard"]


def test_tool_arg_error_when_finish_with_tool_error_and_no_proposal(monkeypatch):
    monkeypatch.setattr(orchestrator.registry, "dispatch",
                        lambda name, args, data: {"result": {"error": "bad arg: target not found"}, "proposal": None})
    tc = lambda i: ToolCall(id=f"c{i}", name="add_node", arguments={})
    script = []
    for i in range(6):
        script.append(LLMResponse(text=None, tool_calls=[tc(i)]))
        script.append(LLMResponse(text="I could not do that.", tool_calls=[]))
    client = FakeLLMClient(script=script)
    evs = _events(client, _sess())
    ta = [e for e in evs if e["type"] == "error" and e.get("kind") == "tool_arg"]
    assert ta and ta[0]["recovery"] == ["edit", "retry"]


def test_build_failure_self_heals_then_finishes(monkeypatch):
    calls = {"n": 0}
    def fake_dispatch(name, args, data):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"result": {"ok": False, "error": "invalid branch 'X'"}, "proposal": None}
        return {"result": {"ok": True}, "proposal": _proposal([])}
    monkeypatch.setattr(orchestrator.registry, "dispatch", fake_dispatch)

    def tc(i):
        return ToolCall(id=f"c{i}", name="scaffold_bot", arguments={})
    client = FakeLLMClient(script=[
        LLMResponse(text=None, tool_calls=[tc(1)]),        # build rejected
        LLMResponse(text="finishing", tool_calls=[]),       # tries to finish -> self-heal backstop
        LLMResponse(text=None, tool_calls=[tc(2)]),        # retry -> clean proposal
        LLMResponse(text="done", tool_calls=[]),            # finish
    ])
    evs = _events(client, _sess())
    assert [e for e in evs if e["type"] == "phase" and e["phase"] == "fixing"]
    assert not [e for e in evs if e["type"] == "error" and e.get("kind") == "tool_arg"]
    assert any(e["type"] == "proposal" for e in evs)
    assert any(e["type"] == "done" for e in evs)


def test_build_failure_gives_up_after_backstops(monkeypatch):
    monkeypatch.setattr(orchestrator.registry, "dispatch",
                        lambda name, args, data: {"result": {"ok": False, "error": "invalid branch 'X'"},
                                                  "proposal": None})
    def tc(i):
        return ToolCall(id=f"c{i}", name="scaffold_bot", arguments={})
    script = []
    for i in range(6):
        script.append(LLMResponse(text=None, tool_calls=[tc(i)]))
        script.append(LLMResponse(text="finish", tool_calls=[]))
    client = FakeLLMClient(script=script)
    evs = _events(client, _sess())
    fixing = [e for e in evs if e["type"] == "phase" and e["phase"] == "fixing"]
    assert len(fixing) <= _MAX_FIX_BACKSTOPS
    assert [e for e in evs if e["type"] == "error" and e.get("kind") == "tool_arg"]
    assert any(e["type"] == "done" for e in evs)
