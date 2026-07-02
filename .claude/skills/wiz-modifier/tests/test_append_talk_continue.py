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
    """Build a minimal two-component export with one multi-round component for testing talk_continue.

    Component A: normal (category:1)
    Component B: multi-round dialogue (category:2)
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
    data["BizSpeechComponent"] = json.dumps([comp0, comp1])
    return data


def _comp_b_details(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    d = comps[1].get("details")
    return json.loads(d) if isinstance(d, str) and d not in ("null", "") else {}


def _comp_b_routes(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    r = comps[1].get("routes")
    return json.loads(r) if isinstance(r, str) and r not in ("null", "") else {}


def _comp_b_top_floor(bundle):
    comps = json.loads(bundle.data["BizSpeechComponent"]) if isinstance(
        bundle.data["BizSpeechComponent"], str) else bundle.data["BizSpeechComponent"]
    tfd = comps[1].get("topFloorDetails")
    return json.loads(tfd) if isinstance(tfd, str) and tfd not in ("null", "") else []


def test_append_talk_continue_node_shape():
    """talk_continue node: type 5, terminal (routes[uuid]=={}), no topFloorDetails,
    optional appoint_node_id = return target componentUuid, optional specificComponentName = return target name.
    Appended INTO a multi-round (category:2) component."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")

    # Append a talk_continue to component B (multi-round, component index 1)
    run_mods(b, [{"op": "append-node", "component": 1,
                  "node": {"id": "respond", "type": "talk_continue",
                           "prompt": "Baik, saya tunggu jawaban Anda."}}],
             manifest_hash="t")

    # Extract component B's details (where we appended)
    comps = json.loads(b.data["BizSpeechComponent"]) if isinstance(
        b.data["BizSpeechComponent"], str) else b.data["BizSpeechComponent"]
    comp_b = comps[1]
    details_b = json.loads(comp_b.get("details", "{}"))

    assert len(details_b) == 1, "expected exactly one node in B's details"
    node_uuid, node_obj = next(iter(details_b.items()))

    # type 5
    assert node_obj["data"]["type"] == 5, "talk_continue must have type 5"

    # terminal: routes[uuid] must be empty dict (no out-edges)
    routes_b = json.loads(comp_b.get("routes", "{}"))
    assert node_uuid in routes_b, f"node {node_uuid} must be in routes"
    assert routes_b[node_uuid] == {}, f"talk_continue routes must be empty, got {routes_b[node_uuid]}"

    # appoint_node_id must be empty (no return target)
    assert node_obj["data"]["appoint_node_id"] == "", \
        "talk_continue without return target: appoint_node_id must be empty"

    # specificComponentName must be empty (no return target)
    assert node_obj["data"]["specificComponentName"] == "", \
        "talk_continue without return target: specificComponentName must be empty"

    # talk_continue does NOT appear in topFloorDetails (unlike exit/goto/goto_kb)
    tfd = json.loads(comp_b.get("topFloorDetails", "[]"))
    tfd_ids = {row.get("id") for row in tfd}
    assert node_uuid not in tfd_ids, \
        "talk_continue node uuid must NOT appear in topFloorDetails"


def test_append_talk_continue_with_return_target():
    """talk_continue with optional return target (config.target = a category:1 component).
    appoint_node_id = target componentUuid, specificComponentName = target name."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")

    # Append a talk_continue to component B (multi-round, component index 1)
    # with return target component A (category:1)
    run_mods(b, [{"op": "append-node", "component": 1,
                  "node": {"id": "respond", "type": "talk_continue",
                           "prompt": "Terima kasih.",
                           "config": {"target": "1. A Canvas"}}}],
             manifest_hash="t")

    # Extract component B's details
    comps = json.loads(b.data["BizSpeechComponent"]) if isinstance(
        b.data["BizSpeechComponent"], str) else b.data["BizSpeechComponent"]
    comp_b = comps[1]
    details_b = json.loads(comp_b.get("details", "{}"))

    node_uuid, node_obj = next(iter(details_b.items()))

    # type 5
    assert node_obj["data"]["type"] == 5, "talk_continue must have type 5"

    # appoint_node_id is the resolved target componentUuid (uuid-a)
    assert node_obj["data"]["appoint_node_id"] == "uuid-a", \
        f"appoint_node_id must be uuid-a (target A's uuid)"

    # specificComponentName is the target name
    assert node_obj["data"]["specificComponentName"] == "1. A Canvas", \
        f"specificComponentName must be 1. A Canvas"

    # multiple_appoint_id must be empty (unlike goto_mr)
    assert node_obj["data"]["multiple_appoint_id"] == "", \
        "talk_continue multiple_appoint_id must be empty"


def test_append_talk_continue_into_non_mr_component_raises():
    """talk_continue appended INTO a category:1 (non-MR) component raises ValueError."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="only valid inside a multi-round"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "respond", "type": "talk_continue",
                               "prompt": "test"}}],
                 manifest_hash="t")


def test_append_talk_continue_mr_target_raises():
    """talk_continue with a category:2 (multi-round) return target raises ValueError.
    Return target must be a category:1 (main-flow) component."""
    data = _make_mr_export()
    # Add a second MR component to test this case
    comps = json.loads(data["BizSpeechComponent"])
    comp_c = dict(comps[0])
    comp_c["name"] = "3. C Canvas"
    comp_c["componentUuid"] = "uuid-c"
    comp_c["sortIndex"] = 3
    comp_c["details"] = "null"
    comp_c["category"] = 2  # another multi-round component
    comps.append(comp_c)
    data["BizSpeechComponent"] = json.dumps(comps)

    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="must be a main-flow \\(non-multi-round\\) component"):
        run_mods(b, [{"op": "append-node", "component": 1,
                      "node": {"id": "respond", "type": "talk_continue",
                               "prompt": "test",
                               "config": {"target": "3. C Canvas"}}}],
                 manifest_hash="t")


def test_append_talk_continue_unknown_target_raises():
    """talk_continue with an unknown return target component name raises ValueError."""
    data = _make_mr_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="does not match any existing component name"):
        run_mods(b, [{"op": "append-node", "component": 1,
                      "node": {"id": "respond", "type": "talk_continue",
                               "prompt": "test",
                               "config": {"target": "NonExistentComponent"}}}],
                 manifest_hash="t")
