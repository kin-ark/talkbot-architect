import orchestrator


def test_system_prompt_covers_new_capabilities():
    s = orchestrator._SYSTEM.lower()
    assert "scaffold_bot" in s
    assert "get_schema" in s
    assert "outline" in s          # outline -> confirm -> build behavior
    assert "confirm" in s
    assert "#node:" in s              # inline node-link convention
    assert "node:<uuid>" in s or "node:uuid" in s
