import agents


def _minimal_params():
    return {
        "name": "Debt Collector",
        "language": "ENG",
        "branch": "dev",
        "canvases": [
            {"name": "1. Greeting",
             "nodes": [{"id": "g-root", "prompt": "Greeting"},
                       {"id": "g-close", "prompt": "Closing"}],
             "edges": [{"from": "g-root", "branch": "Unclassified", "to": "g-close"}]},
        ],
    }


def test_scaffold_produces_checkerclean_doc():
    out = agents.propose_scaffold(_minimal_params())
    assert out["ok"] is True
    assert isinstance(out["proposed_data"], dict)
    # The builder's output must be checker-clean (zero error-severity findings).
    errors = [f for f in agents.validate(out["proposed_data"]) if f["severity"] == "error"]
    assert errors == [], errors


def test_scaffold_rejects_bad_language():
    out = agents.propose_scaffold({**_minimal_params(), "language": "FRA"})
    assert out["ok"] is False
    assert "language" in out["error"].lower()


def test_scaffold_rejects_missing_canvases():
    p = _minimal_params()
    del p["canvases"]
    out = agents.propose_scaffold(p)
    assert out["ok"] is False
    assert "canvas" in out["error"].lower()


def test_scaffold_rejects_empty_canvases():
    out = agents.propose_scaffold({**_minimal_params(), "canvases": []})
    assert out["ok"] is False
    assert "canvas" in out["error"].lower()


def test_scaffold_rejects_bad_branch():
    out = agents.propose_scaffold({**_minimal_params(), "branch": "staging"})
    assert out["ok"] is False
    assert "branch" in out["error"].lower()


def test_scaffold_rejects_unverified_language():
    out = agents.propose_scaffold({**_minimal_params(), "language": "ZHO"})
    assert out["ok"] is False
    assert "language" in out["error"].lower()
