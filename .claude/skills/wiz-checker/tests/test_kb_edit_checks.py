import json, sys
from pathlib import Path
_SK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SK / "wiz-builder" / "scripts"))
from wizbuilder.compile import compile_manifest          # noqa: E402
from wizcheck.parser import parse_dict                    # noqa: E402
from wizcheck.checks.intents import check_intents          # noqa: E402
_FIX = _SK / "wiz-builder" / "tests" / "fixtures"


def _doc(tmp_path, manifest):
    out = tmp_path / "s.json"; compile_manifest(_FIX / manifest, out)
    return json.loads(out.read_text(encoding="utf-8"))


def test_wiz303_clean_goto_kb_passes(tmp_path):
    doc = _doc(tmp_path, "manifest_goto_kb.yaml")    # goto_kb → an existing KB
    codes = [f.code for f in check_intents(parse_dict(doc))]
    assert "WIZ303" not in codes


def test_wiz303_dangling_goto_kb_warns(tmp_path):
    doc = _doc(tmp_path, "manifest_goto_kb.yaml")
    # remove the KB the goto_kb targets, leaving a dangling appoint_knowledge_id
    comps = json.loads(doc["BizSpeechComponent"])
    # find the goto_kb target id from the node, then drop that KB from BizKnowledgeInfo
    target = None
    for c in comps:
        det = json.loads(c["details"])
        for n in det.values():
            if n.get("type") == 8:
                target = n["data"].get("appoint_knowledge_id")
    assert target
    bk = [k for k in json.loads(doc["BizKnowledgeInfo"]) if str(k["knowledgeId"]) != str(target)]
    doc["BizKnowledgeInfo"] = json.dumps(bk)
    findings = [f for f in check_intents(parse_dict(doc)) if f.code == "WIZ303"]
    # WARNING (not ERROR) — an absent KB id may be a legitimate library/external ref,
    # so a dangling jump imports fine; it is a DEPLOY_BLOCKER_CODE (--deploy flags it).
    assert findings and all(f.severity.name == "WARNING" for f in findings)


def test_wiz303_is_a_deploy_blocker_code():
    from wizcheck.report import DEPLOY_BLOCKER_CODES
    assert "WIZ303" in DEPLOY_BLOCKER_CODES


def test_wiz304_empty_user_kb_warns(tmp_path):
    doc = _doc(tmp_path, "manifest_with_kb.yaml")
    bk = json.loads(doc["BizKnowledgeInfo"])
    # empty a user-created KB: clear its kdInfo answers, ensure isInit=0
    target = next(k for k in bk if k.get("isInit", 0) == 0)
    target["kdInfo"] = json.dumps([])
    doc["BizKnowledgeInfo"] = json.dumps(bk)
    findings = [f for f in check_intents(parse_dict(doc)) if f.code == "WIZ304"]
    assert findings and all(f.severity.name == "WARNING" for f in findings)


def test_wiz304_exempts_system_kb(tmp_path):
    doc = _doc(tmp_path, "manifest_with_kb.yaml")
    bk = json.loads(doc["BizKnowledgeInfo"])
    # an isInit=1 system KB with empty kdInfo must NOT warn
    sysk = next((k for k in bk if k.get("isInit") == 1), None)
    if sysk is None:
        import pytest; pytest.skip("no system KB in fixture")
    sysk["kdInfo"] = json.dumps([])
    doc["BizKnowledgeInfo"] = json.dumps(bk)
    codes = [f.code for f in check_intents(parse_dict(doc))]
    assert "WIZ304" not in [c for c in codes]  # exempt


def test_wiz304_clean_bot_passes(tmp_path):
    doc = _doc(tmp_path, "manifest_with_kb.yaml")
    assert "WIZ304" not in [f.code for f in check_intents(parse_dict(doc))]


def test_wiz304_is_a_deploy_blocker_code():
    from wizcheck.report import DEPLOY_BLOCKER_CODES
    assert "WIZ304" in DEPLOY_BLOCKER_CODES
