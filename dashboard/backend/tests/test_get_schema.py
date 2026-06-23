import agents
from tools import registry


def test_get_schema_shape():
    s = agents.get_schema()
    assert set(["manifest_schema", "node_labels", "modifier_ops"]) <= set(s)
    assert isinstance(s["manifest_schema"], dict)
    assert "Greeting" in s["node_labels"]
    assert "add-component" in s["modifier_ops"]


def test_get_schema_tool_dispatch():
    out = registry.dispatch("get_schema", {}, {})
    assert out["proposal"] is None
    assert "manifest_schema" in out["result"]
    assert "get_schema" in [t.name for t in registry.tool_specs()]
