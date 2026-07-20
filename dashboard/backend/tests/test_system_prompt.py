import orchestrator


def test_system_prompt_covers_new_capabilities():
    s = orchestrator._SYSTEM.lower()
    assert "scaffold_bot" in s
    assert "get_schema" in s
    assert "outline" in s          # outline -> confirm -> build behavior
    assert "confirm" in s
    assert "#node:" in s              # inline node-link convention
    assert "node:<uuid>" in s or "node:uuid" in s


def test_system_prompt_explains_talk_branch_model():
    s = orchestrator._SYSTEM.lower()
    assert "branch_intents" in s          # custom-branch declaration named
    assert "system branch" in s           # system branches are automatic
    assert "no answer" in s               # the five system branch names listed
    assert "servicei" in s or "custom" in s   # non-system routing example/wording
