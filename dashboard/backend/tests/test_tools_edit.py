from tools import registry

# A minimal in-memory export with one empty component (index 0).
# componentUuid must be a valid UUID — the checker's parser enforces this.
DATA = {
    "BizSpeechComponent": [{"componentUuid": "00000000-0000-0000-0000-000000000001",
                            "name": "Main", "speechId": 1,
                            "details": "null", "routes": "{}", "inboundPorts": "[]"}],
    "SpeechIntent": [{"intentName": n, "intentId": i} for i, n in
                     enumerate(["Positive", "Negative", "Reject", "Unclassified", "No answer"], 1)],
    "BizKnowledgeInfo": [],
}


def test_tools_registered():
    names = [s.name for s in registry.tool_specs()]
    assert "add_component" in names
    assert "add_node" in names


def test_add_node_returns_proposal():
    out = registry.dispatch("add_node", {"component": 0, "id": "g", "prompt": "Greeting"}, DATA)
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None
    assert isinstance(out["proposal"]["proposed_data"], dict)


def test_add_component_returns_proposal():
    out = registry.dispatch("add_component", {"name": "Greeting"}, DATA)
    assert out["result"]["ok"] is True
    assert out["proposal"] is not None
