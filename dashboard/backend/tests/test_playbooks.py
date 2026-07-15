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


def test_debt_playbook_covers_all_stages():
    text = playbooks.get_playbook("debt_collection")
    for stage in ("Predue", "DPD0", "DPD1-5", "DPD6-30", "Overdue 90", "PTP"):
        assert stage in text, f"playbook missing stage {stage}"
    # quantified: references corpus prevalence
    assert "of 3" in text or "%" in text or "★" in text


def test_debt_playbook_references_corpus_json():
    text = playbooks.get_playbook("debt_collection")
    assert "debt_collection.corpus.json" in text
