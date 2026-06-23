from tools import registry


PARAMS = {
    "name": "Debt Collector", "language": "ENG", "branch": "dev",
    "canvases": [{"name": "1. Greeting",
                  "nodes": [{"id": "g-root", "prompt": "Greeting"},
                            {"id": "g-close", "prompt": "Closing"}],
                  "edges": [{"from": "g-root", "branch": "Unclassified", "to": "g-close"}]}],
}


def test_scaffold_bot_in_specs():
    names = [s.name for s in registry.tool_specs()]
    assert "scaffold_bot" in names


def test_dispatch_scaffold_bot_returns_proposal():
    out = registry.dispatch("scaffold_bot", PARAMS, {})
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_dispatch_scaffold_bot_bad_params_no_proposal():
    out = registry.dispatch("scaffold_bot", {**PARAMS, "language": "FRA"}, {})
    assert out["result"]["ok"] is False
    assert out["proposal"] is None
