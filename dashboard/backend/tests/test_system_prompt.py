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


def test_system_prompt_splits_must_should_and_has_example():
    s = orchestrator._SYSTEM
    low = s.lower()
    assert "must" in low and "should" in low          # rule tiers present
    assert "declare before use" in low                 # generalized ordering rule
    assert "greet" in low and "scaffold_bot" in low    # few-shot example present
