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


def _make_two_comp_export():
    """Build a minimal two-component export for testing cross-component jumps."""
    data = json.loads(BASE.read_text(encoding="utf-8"))
    comps = json.loads(data["BizSpeechComponent"])
    comp0 = comps[0]
    comp0["name"] = "1. A Canvas"
    comp0["componentUuid"] = "uuid-a"
    comp1 = dict(comp0)
    comp1["name"] = "2. B Canvas"
    comp1["componentUuid"] = "uuid-b"
    comp1["sortIndex"] = 2
    comp1["details"] = "null"
    data["BizSpeechComponent"] = json.dumps([comp0, comp1])
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


def test_append_talk_goto_node_shape():
    """talk_goto node: type 9, terminal (routes[uuid]=={}),
    multiple_appoint_id = target componentUuid, specificComponentName = target name.
    Note: talk_goto does NOT appear in topFloorDetails (unlike goto/exit/goto_kb)."""
    data = _make_two_comp_export()
    b = InputBundle(data=data, speech_name="s.json")

    # Append a talk_goto to the first component targeting the second.
    run_mods(b, [{"op": "append-node", "component": 0,
                  "node": {"id": "jump", "type": "talk_goto", "prompt": "goodbye",
                           "config": {"target": "2. B Canvas"}}}],
             manifest_hash="t")

    details = _comp0_details(b)
    assert len(details) == 1, "expected exactly one node in details"
    node_uuid, node_obj = next(iter(details.items()))

    # type 9
    assert node_obj["data"]["type"] == 9, "talk_goto must have type 9"

    # terminal: routes[uuid] must be empty dict (no out-edges)
    routes = _comp0_routes(b)
    assert node_uuid in routes, f"node {node_uuid} must be in routes"
    assert routes[node_uuid] == {}, f"talk_goto routes must be empty, got {routes[node_uuid]}"

    # multiple_appoint_id is the resolved target componentUuid
    assert node_obj["data"]["multiple_appoint_id"] == "uuid-b", \
        f"multiple_appoint_id must be uuid-b"

    # specificComponentName is the target name
    assert node_obj["data"]["specificComponentName"] == "2. B Canvas", \
        f"specificComponentName must be 2. B Canvas"

    # appoint_node_id must be empty
    assert node_obj["data"]["appoint_node_id"] == "", \
        "talk_goto appoint_node_id must be empty"

    # talk_goto does NOT appear in topFloorDetails (unlike goto/goto_kb)
    tfd = _comp0_top_floor(b)
    tfd_ids = {row.get("id") for row in tfd}
    assert node_uuid not in tfd_ids, \
        "talk_goto node uuid must NOT appear in topFloorDetails"


def test_append_talk_goto_unknown_target_raises():
    """talk_goto with an unknown component name raises ValueError."""
    data = _make_two_comp_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="does not match any existing component name"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "talk_goto", "prompt": "gone",
                               "config": {"target": "NonExistentComponent"}}}],
                 manifest_hash="t")


def test_append_talk_goto_missing_target_raises():
    """talk_goto with no config.target raises ValueError (validation gate)."""
    data = _make_two_comp_export()
    b = InputBundle(data=data, speech_name="s.json")
    with pytest.raises(ValueError, match="missing config\\.target"):
        run_mods(b, [{"op": "append-node", "component": 0,
                      "node": {"id": "jump", "type": "talk_goto", "prompt": "",
                               "config": {}}}],
                 manifest_hash="t")
