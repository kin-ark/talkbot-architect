from proposal_meta import change_set, change_summary


def _summary(components):
    return {"components": components, "knowledge_bases": []}


def _comp(uuid, name, nodes):
    return {"uuid": uuid, "name": name, "entry_uuid": None, "root_uuids": [], "nodes": nodes}


def test_added_component_and_nodes():
    before = _summary([])
    after = _summary([_comp("cA", "Greeting", {"n1": {"uuid": "n1", "label": "Hi"}})])
    cs = change_set(before, after)
    assert cs["added_components"] == ["cA"]
    assert cs["added_nodes"] == ["n1"]
    assert cs["changed_nodes"] == [] and cs["removed_nodes"] == []


def test_changed_node_detected():
    before = _summary([_comp("cA", "G", {"n1": {"uuid": "n1", "label": "Hi"}})])
    after = _summary([_comp("cA", "G", {"n1": {"uuid": "n1", "label": "Hello"}})])
    cs = change_set(before, after)
    assert cs["changed_nodes"] == ["n1"]
    assert cs["added_nodes"] == [] and cs["added_components"] == []


def test_removed_node_and_component():
    before = _summary([_comp("cA", "G", {"n1": {"uuid": "n1", "label": "Hi"}}),
                       _comp("cB", "P", {"n2": {"uuid": "n2", "label": "X"}})])
    after = _summary([_comp("cA", "G", {})])
    cs = change_set(before, after)
    assert cs["removed_components"] == ["cB"]
    assert set(cs["removed_nodes"]) == {"n1", "n2"}


def test_change_summary_text():
    cs = {"added_components": ["cA"], "removed_components": [],
          "added_nodes": ["n1", "n2"], "removed_nodes": [], "changed_nodes": []}
    s = change_summary(cs, {"errors_before": 0, "errors_after": 0})
    assert "1 component" in s and "2 nodes" in s and "0 new errors" in s


def test_change_summary_new_errors_and_scaffold():
    cs = {"added_components": [], "removed_components": [], "added_nodes": [],
          "removed_nodes": [], "changed_nodes": ["n1"]}
    assert "⚠ +1 error" in change_summary(cs, {"errors_before": 0, "errors_after": 1})
    # scaffold: checker_delta None → no checker clause, structural parts only
    cs2 = {"added_components": ["cA", "cB"], "removed_components": [], "added_nodes": ["n1"],
           "removed_nodes": [], "changed_nodes": []}
    s2 = change_summary(cs2, None)
    assert "2 components" in s2 and "errors" not in s2
