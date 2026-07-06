import playbooks


def test_list_includes_debt_collection():
    ids = {p["id"] for p in playbooks.list_playbooks()}
    assert "debt_collection" in ids
    entry = next(p for p in playbooks.list_playbooks() if p["id"] == "debt_collection")
    assert entry["title"]  # non-empty title


def test_get_playbook_returns_text_with_anchors():
    txt = playbooks.get_playbook("debt_collection")
    assert txt and "Convincer" in txt and "talk_continue" in txt


def test_get_playbook_unknown_returns_none():
    assert playbooks.get_playbook("nope") is None


def test_get_playbook_rejects_traversal():
    assert playbooks.get_playbook("../main") is None
    assert playbooks.get_playbook("../../etc/passwd") is None
    assert playbooks.get_playbook("sub/dir") is None
