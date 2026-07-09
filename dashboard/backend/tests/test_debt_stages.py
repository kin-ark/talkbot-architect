import json
import agents
import samples


def _raw_list(value):
    return json.loads(value) if isinstance(value, str) else (value or [])


def _build(sid):
    m = samples.load_manifest(sid)
    assert m, f"{sid}: no manifest"
    b = agents.propose_build(m)
    assert b["ok"], f"{sid}: build failed: {b.get('error')}"
    errs = [f for f in agents.validate(b["proposed_data"]) if f["severity"] == "error"]
    assert errs == [], f"{sid}: error findings {errs}"
    return b["proposed_data"]


def _node_type_ints(data):
    out = set()
    for c in _raw_list(data.get("BizSpeechComponent")):
        det = c.get("details")
        if not det or det in ("null", ""):
            continue
        tree = json.loads(det) if isinstance(det, str) else det
        for node in tree.values():
            out.add((node.get("data") or {}).get("type"))
    return out


def _assert_mature(data):
    comps = _raw_list(data.get("BizSpeechComponent"))
    assert len(comps) >= 6
    intents = _raw_list(data.get("SpeechIntent"))
    user = [i for i in intents if str(i.get("isInit")) == "1"]
    assert len(user) >= 12, f"expected >=12 user intents, got {len(user)}"
    kbs = _raw_list(data.get("BizKnowledgeInfo"))
    assert len(kbs) >= 8
    types = _node_type_ints(data)
    assert 7 in types and 10 in types      # conditional + assign
    assert 5 in types                       # talk_continue (multi-round)


def test_dpd0_mature():
    _assert_mature(_build("debt_dpd0"))


def test_dpd1_5_mature():
    _assert_mature(_build("debt_dpd1_5"))


def test_predue_d1_mature():
    _assert_mature(_build("debt_predue_d1"))


def test_dpd6_30_mature():
    _assert_mature(_build("debt_dpd6_30"))


def test_overdue_90_mature():
    _assert_mature(_build("debt_overdue_90"))


def test_ptp_reminder_mature():
    _assert_mature(_build("debt_ptp_reminder"))


def _component_names(data):
    """Extract canvas/component names from built data."""
    names = []
    for c in _raw_list(data.get("BizSpeechComponent")):
        name = c.get("name", "")
        if name:
            names.append(name)
    return names


def test_stages_are_differentiated():
    """Guard per-stage differentiation via component structure and SCS count."""
    predue_data = _build("debt_predue_d1")
    dpd0_data = _build("debt_dpd0")
    dpd6_data = _build("debt_dpd6_30")

    # predue and dpd0 both have 10 base canvases, but dpd6 has 13 (adds 3 convincer tiers)
    predue_comps = _component_names(predue_data)
    dpd0_comps = _component_names(dpd0_data)
    dpd6_comps = _component_names(dpd6_data)

    assert len(predue_comps) == 10, f"predue should have 10 components, got {len(predue_comps)}"
    assert len(dpd0_comps) == 10, f"dpd0 should have 10 components, got {len(dpd0_comps)}"
    assert len(dpd6_comps) == 13, f"dpd6 should have 13 components (extra tiers + DPD Info), got {len(dpd6_comps)}"

    # dpd6 has exclusive components for multi-tier collection
    assert "3. Second Convincer" in dpd6_comps
    assert "4. Third Convincer" in dpd6_comps
    assert "DPD Info" in dpd6_comps

    # These should NOT be in predue/dpd0
    assert "3. Second Convincer" not in predue_comps
    assert "4. Third Convincer" not in predue_comps
    assert "DPD Info" not in predue_comps


def test_debt_samples_have_disposition_tags():
    """Verify all 6 debt-collection samples have disposition tags feature."""
    for sid in ("debt_predue_d1", "debt_dpd0", "debt_dpd1_5", "debt_dpd6_30", "debt_overdue_90", "debt_ptp_reminder"):
        data = _build(sid)
        assert "disposition_tags" in agents.feature_coverage(data)["used"], f"{sid}: no tags"
