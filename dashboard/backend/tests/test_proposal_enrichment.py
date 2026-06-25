from tools import registry


def _session_data():
    return {
        "BizSpeechComponent": [{"componentUuid": "00000000-0000-0000-0000-000000000001",
                                "name": "Main", "speechId": 1, "details": "null",
                                "routes": "{}", "inboundPorts": "[]",
                                "createTime": 1700000000000, "updateTime": 1700000000000}],
        "SpeechIntent": [{"intentName": n, "intentId": i} for i, n in
                         enumerate(["Positive", "Negative", "Reject", "Unclassified", "No answer"], 1)],
        "SpeechVariable": [], "SpeechAudio": [], "BizKnowledgeInfo": [],
    }


def test_add_node_proposal_is_enriched():
    data = _session_data()
    out = registry.dispatch("add_node", {"component": 0, "id": "greet", "prompt": "Greeting"}, data)
    p = out["proposal"]
    assert p is not None
    assert "proposed_summary" in p and isinstance(p["proposed_summary"], dict)
    assert "components" in p["proposed_summary"]
    assert "change_set" in p and "added_nodes" in p["change_set"]
    assert isinstance(p["change_summary"], str) and p["change_summary"]
    assert p["change_set"]["added_nodes"]            # at least one node added


def test_scaffold_proposal_is_enriched():
    out = registry.dispatch("scaffold_bot", {
        "name": "Debt Collector", "language": "ENG", "branch": "dev",
        "canvases": [{"name": "Greeting", "nodes": [{"id": "g", "prompt": "Hi"}], "edges": []}],
    }, _session_data())
    p = out["proposal"]
    assert p is not None and isinstance(p["proposed_summary"], dict)
    assert "change_summary" in p and p["change_summary"]
    assert p["change_set"]["added_components"]       # scaffold adds components
