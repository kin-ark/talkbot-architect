"""WIZ106 routes-key validity tests (M4).

Three cases:
  1. Clean nested build  -> no WIZ106.
  2. Phantom port-key injected into a nested node's routes -> exactly one WIZ106 ERROR.
  3. Terminal node (type 2) with non-empty routes -> WIZ106 ERROR.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup -- cross-skill imports (wiz-builder scripts on sys.path)
# ---------------------------------------------------------------------------
_SKILLS_DIR = Path(__file__).resolve().parents[2]   # .claude/skills/
_BUILDER_SCRIPTS = _SKILLS_DIR / "wiz-builder" / "scripts"
_BUILDER_FIXTURES = _SKILLS_DIR / "wiz-builder" / "tests" / "fixtures"

if str(_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BUILDER_SCRIPTS))

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizcheck.checks.graph import check_graph  # noqa: E402
from wizcheck.parser import parse_dict  # noqa: E402

FIX = _BUILDER_FIXTURES


def _uw(v):
    return json.loads(v) if isinstance(v, str) else v


def _codes(findings):
    return [f.code for f in findings]


def _build(tmp_path, manifest):
    out = tmp_path / "s.json"
    compile_manifest(FIX / manifest, out)
    return json.loads(out.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 1: clean nested build -> no WIZ106
# ---------------------------------------------------------------------------

def test_wiz106_clean_nested_build_passes(tmp_path):
    doc = _build(tmp_path, "manifest_nested.yaml")
    findings = check_graph(parse_dict(doc))
    assert "WIZ106" not in _codes(findings), [str(f) for f in findings if f.code == "WIZ106"]


# ---------------------------------------------------------------------------
# Test 2: phantom port-key injected into a nested node's routes -> 1 WIZ106 ERROR
# ---------------------------------------------------------------------------

def test_wiz106_phantom_route_on_nested_errors(tmp_path):
    doc = _build(tmp_path, "manifest_nested.yaml")
    comps = _uw(doc["BizSpeechComponent"])
    # find the parent component (has a type-11 node), inject a phantom port-key
    for c in comps:
        det = _uw(c["details"])
        routes = _uw(c["routes"])
        nested = next((u for u, n in det.items() if n.get("type") == 11), None)
        if nested:
            routes[nested]["deadbeef-0000-0000-0000-000000000000"] = {
                "source": {"type": 3, "uuid": "deadbeef-0000-0000-0000-000000000000"},
                "target": {"type": 1, "uuid": next(iter(det))},
                "portDetail": {"id": "x", "zIndex": 3},
            }
            c["routes"] = json.dumps(routes)
            break
    doc["BizSpeechComponent"] = json.dumps(comps)
    findings = [f for f in check_graph(parse_dict(doc)) if f.code == "WIZ106"]
    assert len(findings) == 1 and findings[0].severity.name == "ERROR"


# ---------------------------------------------------------------------------
# Test 3: terminal node (type 2) with non-empty routes -> WIZ106 ERROR
# ---------------------------------------------------------------------------

def test_wiz106_terminal_node_with_nonempty_routes_errors(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")  # has an Exit (type 2)
    comps = _uw(doc["BizSpeechComponent"])
    c = comps[0]
    det = _uw(c["details"])
    routes = _uw(c["routes"])
    exit_u = next(u for u, n in det.items() if n.get("type") == 2)
    routes[exit_u] = {"p": {"source": {}, "target": {"uuid": exit_u}, "portDetail": {}}}
    c["routes"] = json.dumps(routes)
    doc["BizSpeechComponent"] = json.dumps(comps)
    assert "WIZ106" in _codes(check_graph(parse_dict(doc)))


# ---------------------------------------------------------------------------
# Test 4: non-terminal node with routes but NO canvas ports -> WIZ106 ERROR
# Regression for the empty-`valid` false-negative — an empty port set must flag
# every routed key as a phantom, not silently let them through.
# ---------------------------------------------------------------------------

def test_wiz106_routes_on_node_with_no_ports_errors(tmp_path):
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    comps = _uw(doc["BizSpeechComponent"])
    c = comps[0]
    det = _uw(c["details"])
    routes = _uw(c["routes"])
    talk_u = next(u for u, n in det.items() if n.get("type") == 1)
    det[talk_u].setdefault("canvas", {}).setdefault("ports", {})["items"] = []
    routes[talk_u] = {
        "ghost-port": {
            "source": {"type": 1, "uuid": "ghost-port"},
            "target": {"type": 1, "uuid": talk_u},
            "portDetail": {"id": "x", "zIndex": 3},
        }
    }
    c["details"] = json.dumps(det)
    c["routes"] = json.dumps(routes)
    doc["BizSpeechComponent"] = json.dumps(comps)
    findings = [f for f in check_graph(parse_dict(doc)) if f.code == "WIZ106"]
    assert findings and all(f.severity.name == "ERROR" for f in findings)


# ---------------------------------------------------------------------------
# WIZ107 + WIZ108: completeness warnings (M4-T2)
# manifest_minimal.yaml = 1 talk node, no Exit, no connected Unclassified
# ---------------------------------------------------------------------------

def test_wiz107_component_without_exit_warns(tmp_path):
    doc = _build(tmp_path, "manifest_minimal.yaml")   # 1 talk node, no terminal
    findings = [f for f in check_graph(parse_dict(doc)) if f.code == "WIZ107"]
    assert findings and all(f.severity.name == "WARNING" for f in findings)


def test_wiz108_talk_without_connected_unclassified_warns(tmp_path):
    doc = _build(tmp_path, "manifest_minimal.yaml")
    findings = [f for f in check_graph(parse_dict(doc)) if f.code == "WIZ108"]
    assert findings and all(f.severity.name == "WARNING" for f in findings)


def test_wiz107_108_are_warnings_not_errors(tmp_path):
    from wizcheck.checks import run_all_checks
    doc = _build(tmp_path, "manifest_minimal.yaml")
    wf = parse_dict(doc)
    findings = run_all_checks(wf)
    errs = [f for f in findings if f.severity.name == "ERROR"]
    assert not any(f.code in ("WIZ107", "WIZ108") for f in errs)
    # Not vacuous: both codes must actually fire (as WARNING) on this incomplete build.
    by_code = {f.code: f for f in findings if f.code in ("WIZ107", "WIZ108")}
    assert set(by_code) == {"WIZ107", "WIZ108"}
    assert all(f.severity.name == "WARNING" for f in by_code.values())
