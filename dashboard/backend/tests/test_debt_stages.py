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
