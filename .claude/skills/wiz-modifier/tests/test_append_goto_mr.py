import json
import sys
from pathlib import Path

import pytest
from wizmodifier.apply import run_mods
from wizmodifier.io import InputBundle

# wiz-builder's scripts dir must be on sys.path for wizbuilder imports.
_SKILL_ROOT = Path(__file__).resolve().parents[3]  # .claude/
_WB_SCRIPTS = _SKILL_ROOT / "skills" / "wiz-builder" / "scripts"
if str(_WB_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WB_SCRIPTS))

from wizbuilder.ids import IdMinter  # noqa: E402

BASELINE = Path(__file__).parent / "fixtures" / "Empty+Dialogue.zip"
BASE = _SKILL_ROOT / "skills" / "wiz-builder" / "templates" / "empty_dialogue.json"


def _load():
    return InputBundle.load(BASELINE)


def _make_mr_export():
    """Build a minimal three-component export with multi-round components for testing goto_mr.

    Component A: normal (category:1)
    Component B: multi-round dialogue (category:2)
    Component C: multi-round dialogue (category:2)
    """
    data = json.loads(BASE.read_text(encoding="utf-8"))
    comps = json.loads(data["BizSpeechComponent"])
    comp0 = comps[0]
    comp0["name"] = "1. A Canvas"
    comp0["componentUuid"] = "uuid-a"
    comp0["category"] = 1  # normal component
    comp1 = dict(comp0)
    comp1["name"] = "2. B Canvas"
    comp1["componentUuid"] = "uuid-b"
    comp1["sortIndex"] = 2
    comp1["details"] = "null"
    comp1["category"] = 2  # multi-round dialogue component
    comp2 = dict(comp0)
    comp2["name"] = "3. C Canvas"
    comp2["componentUuid"] = "uuid-c"
    comp2["sortIndex"] = 3
    comp2["details"] = "null"
    comp2["category"] = 2  # multi-round dialogue component
    data["BizSpeechComponent"] = json.dumps([comp0, comp1, comp2])
    return data


def _comp0_details(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    d = comps[0].get("details")
    return json.loads(d) if isinstance(d, str) and d not in ("null", "") else {}


def _comp0_routes(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    r = comps[0].get("routes")
    return json.loads(r) if isinstance(r, str) and r not in ("null", "") else {}


def _comp0_top_floor(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    tfd = comps[0].get("topFloorDetails")
    return json.loads(tfd) if isinstance(tfd, str) and tfd not in ("null", "") else []


def test_append_goto_mr_node_shape():
    """goto_mr node: type 9, terminal (routes[uuid]=={}),
    multiple_appoint_id = target componentUuid, specificComponentName = target name.
    Note: goto_mr does NOT appear in topFloorDetails (unlike goto/exit/goto_kb).
    Appended INTO a multi-round (category:2) component targeting another multi-round component."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")

    # Append a goto_mr to component B (multi-round, component index 1)
    # targeting component C (multi-round, component index 2).
    run_mods(b, [{"op": "append-node", "component": 1,
                  "node": {"id": "jump", "type": "goto_mr",
                           "config": {"target": "3. C Canvas"}}}],
             manifest_hash="t")

    # Extract component B's details (where we appended)
    comps = json.loads(b.data["BizSpeechComponent"]) if isinstance(
        b.data["BizSpeechComponent"], str) else b.data["BizSpeechComponent"]
    comp_b = comps[1]
    details_b = json.loads(comp_b.get("details", "{}"))

    assert len(details_b) == 1, "expected exactly one node in B's details"
    node_uuid, node_obj = next(iter(details_b.items()))

    # type 9
    assert node_obj["data"]["type"] == 9, "goto_mr must have type 9"

    # terminal: routes[uuid] must be empty dict (no out-edges)
    routes_b = json.loads(comp_b.get("routes", "{}"))
    assert node_uuid in routes_b, f"node {node_uuid} must be in routes"
    assert routes_b[node_uuid] == {}, f"goto_mr routes must be empty, got {routes_b[node_uuid]}"

    # multiple_appoint_id is the resolved target componentUuid (uuid-c)
    assert node_obj["data"]["multiple_appoint_id"] == "uuid-c", \
        f"multiple_appoint_id must be uuid-c"

    # specificComponentName is the target name
    assert node_obj["data"]["specificComponentName"] == "3. C Canvas", \
        f"specificComponentName must be 3. C Canvas"

    # appoint_node_id must be empty
    assert node_obj["data"]["appoint_node_id"] == "", \
        "goto_mr appoint_node_id must be empty"

    # goto_mr does NOT appear in topFloorDetails (unlike goto/goto_kb)
    tfd = json.loads(comp_b.get("topFloorDetails", "[]"))
    tfd_ids = {row.get("id") for row in tfd}
    assert node_uuid not in tfd_ids, \
        "goto_mr node uuid must NOT appear in topFloorDetails"


def test_append_goto_mr_into_non_mr_component_raises():
    """goto_mr appended INTO a category:1 (non-MR) component raises ValueError,
    even when targeting a category:2 component."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="only valid inside a multi-round"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "goto_mr",
                               "config": {"target": "2. B Canvas"}}}],
                 manifest_hash="t")


def test_append_goto_mr_non_mr_target_raises():
    """goto_mr targeting a category:1 (non-MR) component raises ValueError.
    Appended INTO a category:2 component, but targeting a category:1 component."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="is not a multi-round \\(category:2\\) component"):
        run_mods(b, [{"op": "append-node", "component": 1,
                      "node": {"id": "jump", "type": "goto_mr",
                               "config": {"target": "1. A Canvas"}}}],
                 manifest_hash="t")


def test_append_goto_mr_unknown_target_raises():
    """goto_mr with an unknown component name raises ValueError."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="does not match any existing component name"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "goto_mr",
                               "config": {"target": "NonExistentComponent"}}}],
                 manifest_hash="t")


def test_append_goto_mr_missing_target_raises():
    """goto_mr with no config.target raises ValueError (validation gate)."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="missing config\\.target"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "goto_mr",
                               "config": {}}}],
                 manifest_hash="t")
