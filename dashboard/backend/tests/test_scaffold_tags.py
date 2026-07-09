import agents
from tools import registry


def test_scaffold_bot_schema_has_tags():
    spec = next(t for t in registry.tool_specs() if t.name == "scaffold_bot")
    props = spec.parameters["properties"]
    assert "tags" in props                       # top-level categories
    node_props = props["canvases"]["items"]["properties"]["nodes"]["items"]["properties"]
    assert "tags" in node_props                  # per-node tags


def test_propose_scaffold_authors_tags():
    params = {
        "name": "Tag Bot", "language": "IDN", "branch": "dev",
        "tags": [{"name": "Disposition", "values": ["PTP", "Refused"]}],
        "canvases": [{
            "name": "Main",
            "nodes": [
                {"id": "greet", "prompt": "Halo"},
                {"id": "bye", "type": "exit", "prompt": "Terima kasih",
                 "tags": [{"category": "Disposition", "values": ["PTP"]}]},
            ],
            "edges": [{"from": "greet", "branch": "Unclassified", "to": "bye"}],
        }],
    }
    r = agents.propose_scaffold(params)
    assert r["ok"], r.get("error")
    data = r["proposed_data"]
    errs = [f for f in agents.validate(data) if f["severity"] == "error"]
    assert errs == []
    assert "disposition_tags" in agents.feature_coverage(data)["used"]
