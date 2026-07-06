import agents
import json
import samples


def _raw_list(value):
    return json.loads(value) if isinstance(value, str) else (value or [])


def test_registry_shape():
    listed = samples.list_samples()
    for e in listed:
        assert set(e) == {"id", "title", "description"}
    ids = {e["id"] for e in listed}
    assert {"greeting_faq", "debt_collector", "appointment_booking", "debt_dpd0", "debt_dpd1_5", "debt_dpd6_30"} <= ids
    assert len(listed) >= 4


def test_every_sample_builds_clean():
    for entry in samples.SAMPLES:
        sid = entry["id"]
        manifest = samples.load_manifest(sid)
        assert manifest, f"{sid}: no manifest"
        built = agents.propose_build(manifest)
        assert built["ok"], f"{sid}: build failed: {built.get('error')}"
        errs = [f for f in agents.validate(built["proposed_data"]) if f["severity"] == "error"]
        assert errs == [], f"{sid}: error findings {errs}"


def test_load_manifest_and_title_unknown_id():
    assert samples.load_manifest("nope") is None
    assert samples.title_of("nope") is None
    assert samples.title_of("greeting_faq") == "Greeting & FAQ"


def test_debt_preset_is_mature():
    manifest = samples.load_manifest("debt_collector")
    built = agents.propose_build(manifest)
    assert built["ok"], f"build failed: {built.get('error')}"
    data = built["proposed_data"]

    comps = _raw_list(data.get("BizSpeechComponent"))
    assert len(comps) >= 6, f"expected >=6 components, got {len(comps)}"

    kb_titles = {kb.get("kdTitle") for kb in _raw_list(data.get("BizKnowledgeInfo"))}
    expected_kbs = {"KBB3 Forgot to Pay", "KBB8 Penalty Non-Payment",
                    "KBB9 Special Circumstances", "How to Pay"}
    assert expected_kbs <= kb_titles, f"missing business KBs: {expected_kbs - kb_titles}"

    node_type_ints = set()
    for c in comps:
        det = c.get("details")
        if not det or det in ("null", ""):
            continue
        tree = json.loads(det) if isinstance(det, str) else det
        for node in tree.values():
            node_type_ints.add((node.get("data") or {}).get("type"))
    assert 7 in node_type_ints, "expected a conditional (type 7) node"
    assert 10 in node_type_ints, "expected an assign (type 10) node"
