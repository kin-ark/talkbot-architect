"""Tests for wizbuilder.knowledge — apply_knowledge_bases step (KB-T2)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from wizbuilder.canvases import apply_canvases
from wizbuilder.compile import compile_manifest
from wizbuilder.identity import apply_identity
from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.intents import apply_intents
from wizbuilder.knowledge import apply_knowledge_bases
from wizbuilder.manifest import load_manifest
from wizbuilder.variables import apply_variables

SKILL_DIR = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_DIR / "tests" / "fixtures"
TEMPLATE_PATH = SKILL_DIR / "templates" / "empty_dialogue.json"

# Ground-truth template KB (knowledgeId 179824) from a real deploy-verified export.
# SKILL_DIR = .../kb-authoring/.claude/skills/wiz-builder
# parents[2] = .../kb-authoring  (worktree root where talkbot/ lives)
_REPO_ROOT = SKILL_DIR.parents[2]
_GROUND_TRUTH_EXPORT = (
    _REPO_ROOT / "talkbot" / "Tiktok+Paylater+DPD0" / "speech4892384019254584542.json"
)

# UUID4 pattern (case-insensitive hex, standard hyphenated form)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _build_pipeline(manifest_name: str) -> tuple[dict, object, IdMinter, dict, dict]:
    """Run the full pipeline up to and including apply_canvases.

    Returns (template, manifest, minter, kb_id_by_name, canvas_uuid_by_name).
    """
    manifest = load_manifest(FIXTURES / manifest_name)
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)

    kb_id_by_name: dict[str, int] = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }

    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )
    return template, manifest, minter, kb_id_by_name, canvas_uuid_by_name


# ---------------------------------------------------------------------------
# KB-T2 tests
# ---------------------------------------------------------------------------


def test_biz_knowledge_info_has_new_entry(template_dict, fixture_path):
    """apply_knowledge_bases appends a BizKnowledgeInfo entry for each KB."""
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    # Run full pipeline up to apply_canvases
    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )

    # Count before
    bk_before = json.loads(template["BizKnowledgeInfo"])
    before_count = len(bk_before)

    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )

    bk_after = json.loads(template["BizKnowledgeInfo"])
    assert len(bk_after) == before_count + 1

    # Find the new entry
    new_entry = next(e for e in bk_after if e["kdTitle"] == "Payment FAQ")
    assert new_entry["kdTitle"] == "Payment FAQ"
    assert new_entry["answerType"] == 1
    assert new_entry["knowledgeId"] == kb_id_by_name["Payment FAQ"]


def test_biz_knowledge_info_intents_resolved(template_dict, fixture_path):
    """The intents field JSON-decodes to the correct resolved intentId."""
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )

    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )

    bk_after = json.loads(template["BizKnowledgeInfo"])
    new_entry = next(e for e in bk_after if e["kdTitle"] == "Payment FAQ")

    # intents is a JSON-encoded string
    resolved_intents = json.loads(new_entry["intents"])
    assert isinstance(resolved_intents, list)
    assert len(resolved_intents) == 1
    assert resolved_intents[0]["intentName"] == "AskPayment"
    # intentId must be the minted id for the custom intent
    expected_intent_id = minter.int_id("intent:AskPayment")
    assert resolved_intents[0]["intentId"] == expected_intent_id


def test_biz_knowledge_info_kd_info_has_speak_xml(template_dict, fixture_path):
    """kdInfo JSON-decodes to items with the <speak…> xml wrapper."""
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )

    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )

    bk_after = json.loads(template["BizKnowledgeInfo"])
    new_entry = next(e for e in bk_after if e["kdTitle"] == "Payment FAQ")

    kd_info = json.loads(new_entry["kdInfo"])
    assert len(kd_info) == 2  # two answers

    # Each item must have a <speak…> xml wrapper
    for item in kd_info:
        assert "editorValue" in item
        xml = item["editorValue"]["xml"]
        assert xml.startswith('<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">')
        assert item["answer"] in xml
        assert item["answerType"] == 1

    answer_texts = {item["answer"] for item in kd_info}
    assert "Pembayaran bisa dilakukan melalui transfer bank." in answer_texts
    assert "Anda bisa bayar melalui aplikasi kami." in answer_texts


def test_sentence_cut_knowledge_rows_emitted(template_dict, fixture_path):
    """SentenceCutKnowledge gains one row per answer for the new KB."""
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )

    sck_before = json.loads(template.get("SentenceCutKnowledge", "[]"))
    before_count = len(sck_before)

    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )

    sck_after = json.loads(template["SentenceCutKnowledge"])
    # Two answers → two new SCK rows
    assert len(sck_after) == before_count + 2

    kb_id = kb_id_by_name["Payment FAQ"]
    kb_rows = [r for r in sck_after if r["knowledgeId"] == kb_id]
    assert len(kb_rows) == 2

    texts = {r["sentenceText"] for r in kb_rows}
    assert "Pembayaran bisa dilakukan melalui transfer bank." in texts
    assert "Anda bisa bayar melalui aplikasi kami." in texts

    for row in kb_rows:
        assert row["branch"] == "dev"
        assert row["isDelete"] == 0
        assert row["showType"] == 0
        assert row["type"] == "record"
        assert row["knowledgeId"] == kb_id


def test_talk_node_allow_jump_knowledges_includes_new_kb(template_dict, fixture_path):
    """A talk node's allow_jump_knowledges includes the new KB's knowledgeId."""
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )

    kb_id = kb_id_by_name["Payment FAQ"]

    # Inspect the rendered canvas to check allow_jump_knowledges
    bsc = json.loads(template["BizSpeechComponent"])
    main_canvas = next(c for c in bsc if c["name"] == "1. Main")
    details = json.loads(main_canvas["details"])

    # Find any talk node
    talk_nodes = [n for n in details.values() if n.get("type") == 1]
    assert talk_nodes, "Expected at least one talk node in '1. Main'"

    for node in talk_nodes:
        ajk = node["data"]["allow_jump_knowledges"]
        assert str(kb_id) in ajk, (
            f"KB id {kb_id!r} not in allow_jump_knowledges: {ajk!r}"
        )


def test_no_kb_manifest_unchanged(template_dict, fixture_path):
    """Existing KB-less manifests produce no change to BizKnowledgeInfo or SentenceCutKnowledge."""
    manifest = load_manifest(fixture_path("manifest_minimal.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name: dict = {}
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )

    bk_before = json.loads(template["BizKnowledgeInfo"])
    sck_before = json.loads(template.get("SentenceCutKnowledge", "[]"))

    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )

    bk_after = json.loads(template["BizKnowledgeInfo"])
    sck_after = json.loads(template.get("SentenceCutKnowledge", "[]"))

    assert len(bk_after) == len(bk_before), (
        "BizKnowledgeInfo should not change for KB-less manifest"
    )
    assert len(sck_after) == len(sck_before), (
        "SentenceCutKnowledge should not change for KB-less manifest"
    )


def test_kb_via_compile_manifest_checker_clean(tmp_path):
    """A manifest with a KB compiles without checker errors (end-to-end)."""
    out = tmp_path / "speech.json"
    result = compile_manifest(FIXTURES / "manifest_with_kb.yaml", out)
    assert result.checker_errors == 0, (
        f"compile produced {result.checker_errors} checker errors: {result.finding_codes}"
    )


# ---------------------------------------------------------------------------
# KB-T2 fix-pass: deploy-risk field coverage + speechRecCutId format
# ---------------------------------------------------------------------------


def _run_apply_kb(template_dict, fixture_path) -> tuple[dict, dict]:
    """Helper: run the full pipeline up to apply_knowledge_bases and return
    (built_kb_entry, minter) for the 'Payment FAQ' KB."""
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )
    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )
    bk_after = json.loads(template["BizKnowledgeInfo"])
    built_kb = next(e for e in bk_after if e["kdTitle"] == "Payment FAQ")
    return built_kb, template


def test_biz_knowledge_info_key_superset_of_template(template_dict, fixture_path):
    """Built KB entry must have at least all keys present in the real template KB
    (knowledgeId 179824 from speech4892384019254584542.json).

    This is the deploy-risk guard: missing fields → opaque WIZ deploy failures.
    Previously missing: repeatScriptType, tagList.
    """
    if not _GROUND_TRUTH_EXPORT.exists():
        import pytest
        pytest.skip(f"Ground-truth export not found: {_GROUND_TRUTH_EXPORT}")

    # Load the real template KB key set
    with _GROUND_TRUTH_EXPORT.open(encoding="utf-8") as fh:
        gt_data = json.load(fh)
    bk_raw = gt_data.get("BizKnowledgeInfo", "[]")
    bk_list = json.loads(bk_raw) if isinstance(bk_raw, str) else bk_raw
    template_kb = next(kb for kb in bk_list if kb.get("knowledgeId") == 179824)
    template_keys = set(template_kb.keys())

    built_kb, _ = _run_apply_kb(template_dict, fixture_path)
    built_keys = set(built_kb.keys())

    missing = template_keys - built_keys
    assert not missing, (
        f"Built KB entry is missing fields vs ground-truth template KB: {sorted(missing)}"
    )


def test_biz_knowledge_info_instance_stat_fields_reset(template_dict, fixture_path):
    """New-KB instance/stat fields must be reset to zero, NOT copied from template.

    recordNum=0 (no recordings), wordNum=0 (no words), isInit=0 (user-created).
    The template KB has isInit:1 (system-init) and non-zero recordNum/wordNum.
    """
    built_kb, _ = _run_apply_kb(template_dict, fixture_path)

    assert built_kb["recordNum"] == 0, (
        f"recordNum should be 0 for a new KB, got {built_kb['recordNum']!r}"
    )
    assert built_kb["wordNum"] == 0, (
        f"wordNum should be 0 for a new KB, got {built_kb['wordNum']!r}"
    )
    assert built_kb["isInit"] == 0, (
        f"isInit should be 0 (user-created) for a new KB, got {built_kb['isInit']!r}"
    )


def test_sentence_cut_knowledge_speech_rec_cut_id_is_uuid(template_dict, fixture_path):
    """Each SentenceCutKnowledge row's speechRecCutId must be a UUID-format string.

    Real rows use UUID4 format: "781f1a53-0d7b-4d88-a34c-49e1000fba38".
    The previous implementation emitted a wide-int string, which caused deploy
    failures.  knowledgeRecCutId must remain an int (matches real row types).
    """
    manifest = load_manifest(fixture_path("manifest_with_kb.yaml"))
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = template_dict
    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    kb_id_by_name = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
        if kb.multi_round is None
    }
    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )
    apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )

    sck_after = json.loads(template["SentenceCutKnowledge"])
    kb_id = kb_id_by_name["Payment FAQ"]
    kb_rows = [r for r in sck_after if r["knowledgeId"] == kb_id]
    assert kb_rows, "Expected SCK rows for 'Payment FAQ' KB"

    for row in kb_rows:
        speech_rec_cut_id = row["speechRecCutId"]
        assert isinstance(speech_rec_cut_id, str), (
            f"speechRecCutId must be a str, got {type(speech_rec_cut_id).__name__}: "
            f"{speech_rec_cut_id!r}"
        )
        assert _UUID_RE.match(speech_rec_cut_id), (
            f"speechRecCutId must be UUID-format, got {speech_rec_cut_id!r}"
        )
        # knowledgeRecCutId must remain an int (real rows: int)
        assert isinstance(row["knowledgeRecCutId"], int), (
            f"knowledgeRecCutId must be int, got {type(row['knowledgeRecCutId']).__name__}"
        )
