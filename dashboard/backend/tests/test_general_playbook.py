"""Tests for general playbook (Task 3)."""
from __future__ import annotations

import agents
import playbooks


def test_general_playbook_present():
    """General playbook is in the list and has content."""
    assert "general" in {p["id"] for p in playbooks.list_playbooks()}
    txt = playbooks.get_playbook("general")
    assert txt and "Unclassified" in txt and "Exit" in txt


def test_get_playbook_unknown_falls_back_to_general():
    """Unknown vertical still returns general guidance."""
    r = agents.get_playbook("no_such_vertical")
    assert r["found"] is False
    assert r.get("general")            # general guidance always provided
    assert "Unclassified" in r["general"]


def test_get_playbook_known_vertical_still_works():
    """Known vertical returns both vertical playbook and general."""
    r = agents.get_playbook("debt_collection")
    assert r["found"] is True and r["playbook"]
    assert r.get("general")  # general is also always present
