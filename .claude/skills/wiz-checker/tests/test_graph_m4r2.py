"""WIZ109 true-orphan tests (M4 round-2).

An orphan = a non-entry node with zero inbound same-component edges. WARNING.
Catches deploy-blocking orphans even when WIZ101 (reachability) skips a
root-less component.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SKILLS_DIR = Path(__file__).resolve().parents[2]          # .claude/skills/
_REPO_ROOT = _SKILLS_DIR.parents[1]                         # repo root
_BUILDER_SCRIPTS = _SKILLS_DIR / "wiz-builder" / "scripts"
_BUILDER_FIXTURES = _SKILLS_DIR / "wiz-builder" / "tests" / "fixtures"

if str(_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BUILDER_SCRIPTS))

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizcheck.checks.graph import check_graph      # noqa: E402
from wizcheck.parser import parse_dict             # noqa: E402

FIX = _BUILDER_FIXTURES


def _uw(v):
    return json.loads(v) if isinstance(v, str) else v


def _build(tmp_path, manifest):
    out = tmp_path / "s.json"
    compile_manifest(FIX / manifest, out)
    return json.loads(out.read_text(encoding="utf-8"))


def _raw_comp(doc, comp_uuid):
    """Return (comps_list, the raw component dict whose componentUuid matches)."""
    comps = _uw(doc["BizSpeechComponent"])
    for c in comps:
        if c.get("componentUuid") == comp_uuid:
            return comps, c
    raise AssertionError(f"component {comp_uuid!r} not in export")


def _pick_inbound_victim(comp):
    """A non-entry node in `comp` that currently has same-component inbound."""
    inbound = {
        b.target_uuid
        for n in comp.nodes.values()
        for b in n.branches
        if b.target_uuid is not None and b.target_uuid in comp.nodes
    }
    return next(u for u in inbound if u != comp.entry_uuid)


def _strip_inbound(routes, victim):
    """Delete every route edge whose target uuid == victim (orphans it)."""
    for portmap in routes.values():
        for port in list(portmap):
            tgt = (portmap[port].get("target") or {}).get("uuid")
            if tgt == victim:
                del portmap[port]


def test_wiz109_clean_build_passes(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    codes = [f.code for f in check_graph(parse_dict(doc))]
    assert "WIZ109" not in codes


def test_wiz109_orphan_node_warns(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = parse_dict(doc).flow_model.components[0]
    victim = _pick_inbound_victim(comp)
    comps, c = _raw_comp(doc, comp.uuid)
    routes = _uw(c["routes"])
    _strip_inbound(routes, victim)
    c["routes"] = json.dumps(routes)
    doc["BizSpeechComponent"] = json.dumps(comps)
    findings = [f for f in check_graph(parse_dict(doc)) if f.code == "WIZ109"]
    assert any(f.location.id == victim for f in findings)
    assert all(f.severity.name == "WARNING" for f in findings)


def test_wiz109_fires_on_rootless_component_where_wiz101_silent(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comp = parse_dict(doc).flow_model.components[0]
    victim = _pick_inbound_victim(comp)
    comps, c = _raw_comp(doc, comp.uuid)
    det = _uw(c["details"])
    routes = _uw(c["routes"])
    for u in det:                       # make the component root-less
        det[u].pop("is_default", None)
    _strip_inbound(routes, victim)      # and orphan the victim
    c["details"] = json.dumps(det)
    c["routes"] = json.dumps(routes)
    doc["BizSpeechComponent"] = json.dumps(comps)
    findings = check_graph(parse_dict(doc))
    wiz101 = [f for f in findings if f.code == "WIZ101" and f.location.id == victim]
    wiz109 = [f for f in findings if f.code == "WIZ109" and f.location.id == victim]
    assert not wiz101, "WIZ101 must skip a root-less component"
    assert wiz109 and all(f.severity.name == "WARNING" for f in wiz109)


def test_wiz109_zero_on_real_nested_export():
    real = _REPO_ROOT / "talkbot" / "Test+Kinan" / "speech13139256226648334285.json"
    if not real.exists():
        import pytest
        pytest.skip("real nested export not present in this checkout")
    doc = json.loads(real.read_text(encoding="utf-8"))
    findings = [f for f in check_graph(parse_dict(doc)) if f.code == "WIZ109"]
    assert findings == [], [str(f) for f in findings]
