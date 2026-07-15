import orchestrator


def test_system_prompt_pushes_seed_first():
    s = orchestrator._SYSTEM
    assert "list_samples" in s and "get_sample" in s and "get_debt_corpus" in s
    # seed-first intent: prefer adapting a sample via build over scaffolding from scratch
    low = s.lower()
    assert "get_sample" in s and "build" in low
    assert "from scratch" in low or "rather than" in low
