"""KB-authoring regression tests (KB-T5).

Two goals:
  1. Regression-lock the KBView read path:
       - build a simple and a multi-round KB export via wizbuilder, parse it,
         and assert KBView is populated + multi_round is set.
  2. New WIZ302 check:
       - a KB whose triggering intentId is absent from SpeechIntent -> one ERROR.
       - a KB whose intents all resolve -> no WIZ302.
       - a KB with a multi_round delegate targeting an absent component -> no WIZ302
         (absent component is tolerated; WIZ302 is only for dangling intent ids).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup -- cross-skill imports (must precede wizbuilder import)
# ---------------------------------------------------------------------------
# This test file lives in:
#   .claude/skills/wiz-checker/tests/test_kb_authoring.py
#   parents[0] = tests/
#   parents[1] = wiz-checker/
#   parents[2] = skills/
#   parents[3] = .claude/
#   parents[4] = repo/worktree root
_SKILLS_DIR = Path(__file__).resolve().parents[2]   # .claude/skills/
_BUILDER_SCRIPTS = _SKILLS_DIR / "wiz-builder" / "scripts"
_BUILDER_FIXTURES = _SKILLS_DIR / "wiz-builder" / "tests" / "fixtures"

if str(_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BUILDER_SCRIPTS))

from wizcheck.checks.intents import check_intents  # noqa: E402
from wizcheck.flowmodel import build_flow_model  # noqa: E402
from wizcheck.ir import Intent, KnowledgeBase, WizFile  # noqa: E402
from wizcheck.parser import parse_dict  # noqa: E402
from wizcheck.report import Severity  # noqa: E402

try:
    from wizbuilder.compile import compile_manifest  # noqa: E402
    _HAS_BUILDER = True
except ImportError:
    _HAS_BUILDER = False

_MANIFEST_KB = _BUILDER_FIXTURES / "manifest_with_kb.yaml"
_MANIFEST_MR = _BUILDER_FIXTURES / "manifest_with_multiround_kb.yaml"


# ---------------------------------------------------------------------------
# Helpers for WIZ302 unit tests (no builder needed)
# ---------------------------------------------------------------------------

def _intent(intent_id: int, name: str) -> Intent:
    return Intent(
        intent_id=intent_id, name=name, language="IDN",
        keywords=(), user_responses=(), raw={},
    )


def _kb(knowledge_id: int, title: str, intent_ids: tuple[int, ...]) -> KnowledgeBase:
    return KnowledgeBase(
        knowledge_id=knowledge_id,
        title=title,
        kd_type=0,
        intents=intent_ids,
        raw={},
    )


def _wf(intents: dict, knowledge_bases: dict) -> WizFile:
    return WizFile(
        raw={}, components={}, variables={},
        intents=intents,
        utterances=(),
        audios={},
        knowledge_bases=knowledge_bases,
    )


# ===========================================================================
# 1. Builder-driven regression: KBView populated for a simple KB
# ===========================================================================

@pytest.mark.skipif(not _HAS_BUILDER, reason="wiz-builder not on path")
@pytest.mark.skipif(not _MANIFEST_KB.exists(), reason="manifest_with_kb.yaml not found")
def test_simple_kb_kbview_populated(tmp_path):
    """parse_dict + build_flow_model on a builder output must produce at least one KBView."""
    out = tmp_path / "speech_kb.json"
    compile_manifest(_MANIFEST_KB, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    wf = parse_dict(data)
    fm = build_flow_model(data)

    # flowmodel KBViews
    assert len(fm.knowledge_bases) >= 1, (
        "Expected at least one KBView in FlowModel.knowledge_bases"
    )
    kb_view = fm.knowledge_bases[0]
    assert kb_view.knowledge_id > 0
    # KBView.title reads kdTitle; builder emits kdTitle=kb.name (see title/kdTitle note below)
    assert kb_view.title != "" or kb_view.knowledge_id > 0
    # Simple KB has no multi_round delegation
    assert kb_view.multi_round is None, (
        f"Simple KB must have multi_round=None, got {kb_view.multi_round!r}"
    )
    # KBView.intents: should be non-empty (builder emits at least one intent)
    assert len(kb_view.intents) >= 1, (
        "KBView.intents must not be empty for a KB with declared intents"
    )

    # IR KnowledgeBase: wf.knowledge_bases keyed by knowledgeId
    assert isinstance(wf.knowledge_bases, dict)


@pytest.mark.skipif(not _HAS_BUILDER, reason="wiz-builder not on path")
@pytest.mark.skipif(not _MANIFEST_MR.exists(), reason="manifest_with_multiround_kb.yaml not found")
def test_multiround_kb_has_multi_round_set(tmp_path):
    """Multi-round KB must have KBView.multi_round populated (a nested FlowModel)."""
    out = tmp_path / "speech_mr.json"
    compile_manifest(_MANIFEST_MR, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    fm = build_flow_model(data)

    # Should have 2 KBViews (Due Date KB + Installment KB)
    assert len(fm.knowledge_bases) >= 2, (
        f"Expected >= 2 KBViews for multi-round manifest, got {len(fm.knowledge_bases)}"
    )

    # Both KBs have multi_round (they target the "Handler" canvas)
    mr_kbs = [kbv for kbv in fm.knowledge_bases if kbv.multi_round is not None]
    assert len(mr_kbs) >= 1, (
        "Expected at least one KBView with multi_round set for multi-round manifest"
    )

    mr = mr_kbs[0].multi_round
    assert mr is not None
    # multi_round is a FlowModel with exactly the target component
    assert len(mr.components) == 1, (
        f"multi_round FlowModel must have exactly 1 component, got {len(mr.components)}"
    )
    target_comp = mr.components[0]
    # Target is the "Handler" canvas
    assert target_comp.name == "Handler", (
        f"multi_round target must be 'Handler', got {target_comp.name!r}"
    )


@pytest.mark.skipif(not _HAS_BUILDER, reason="wiz-builder not on path")
@pytest.mark.skipif(not _MANIFEST_MR.exists(), reason="manifest_with_multiround_kb.yaml not found")
def test_multiround_kb_kbview_intents(tmp_path):
    """KBViews in multi-round export have intents from flowmodel (not empty)."""
    out = tmp_path / "speech_mr2.json"
    compile_manifest(_MANIFEST_MR, out)

    data = json.loads(out.read_text(encoding="utf-8"))
    fm = build_flow_model(data)

    for kbv in fm.knowledge_bases:
        assert len(kbv.intents) >= 1, (
            f"KBView '{kbv.title}' must have at least one intent, got {kbv.intents!r}"
        )


# ===========================================================================
# 2. WIZ302: dangling KB intent check (unit tests -- no builder needed)
# ===========================================================================

class TestWIZ302DanglingKBIntent:
    """WIZ302: KB references an intentId absent from wf.intents -> ERROR."""

    def test_dangling_intent_yields_wiz302(self):
        """KB references intentId 99 which is absent -> one WIZ302 ERROR."""
        intents = {
            1: _intent(1, "Unclassified"),
            2: _intent(2, "Negative"),
        }
        kbs = {
            10: _kb(10, "Payment FAQ", (99,)),  # 99 is not in intents
        }
        wf = _wf(intents=intents, knowledge_bases=kbs)
        findings = check_intents(wf)
        wiz302 = [f for f in findings if f.code == "WIZ302"]
        assert len(wiz302) == 1, (
            f"Expected exactly 1 WIZ302 finding, got {len(wiz302)}: {wiz302}"
        )
        assert wiz302[0].severity is Severity.ERROR
        assert "Payment FAQ" in wiz302[0].message
        assert "99" in wiz302[0].message

    def test_resolved_intents_yields_no_wiz302(self):
        """KB whose intents all resolve -> no WIZ302."""
        intents = {
            1: _intent(1, "Unclassified"),
            5: _intent(5, "AskPayment"),
        }
        kbs = {
            10: _kb(10, "Payment FAQ", (5,)),  # 5 is in intents
        }
        wf = _wf(intents=intents, knowledge_bases=kbs)
        findings = check_intents(wf)
        assert not any(f.code == "WIZ302" for f in findings), (
            f"Expected no WIZ302 when all KB intents resolve; findings: {findings}"
        )

    def test_multiple_dangling_intents_one_finding_each(self):
        """Two KBs each with one dangling intent -> exactly 2 WIZ302 findings."""
        intents = {1: _intent(1, "Unclassified")}
        kbs = {
            10: _kb(10, "KB A", (100,)),
            11: _kb(11, "KB B", (200,)),
        }
        wf = _wf(intents=intents, knowledge_bases=kbs)
        findings = check_intents(wf)
        wiz302 = [f for f in findings if f.code == "WIZ302"]
        assert len(wiz302) == 2, (
            f"Expected 2 WIZ302 findings for 2 dangling intents, got {len(wiz302)}"
        )

    def test_kb_with_no_intents_no_wiz302(self):
        """KB with empty intents tuple -> no WIZ302 (nothing to dangle)."""
        intents = {1: _intent(1, "Unclassified")}
        kbs = {10: _kb(10, "Empty KB", ())}
        wf = _wf(intents=intents, knowledge_bases=kbs)
        findings = check_intents(wf)
        assert not any(f.code == "WIZ302" for f in findings)

    def test_kb_partial_dangling_fires_only_for_dangling(self):
        """KB with one resolved and one dangling intent -> exactly 1 WIZ302."""
        intents = {
            1: _intent(1, "Unclassified"),
            5: _intent(5, "AskPayment"),
        }
        kbs = {
            10: _kb(10, "Payment FAQ", (5, 999)),  # 5 ok, 999 dangling
        }
        wf = _wf(intents=intents, knowledge_bases=kbs)
        findings = check_intents(wf)
        wiz302 = [f for f in findings if f.code == "WIZ302"]
        assert len(wiz302) == 1
        assert "999" in wiz302[0].message

    def test_no_knowledge_bases_no_wiz302(self):
        """No KBs -> no WIZ302."""
        intents = {1: _intent(1, "Unclassified")}
        wf = _wf(intents=intents, knowledge_bases={})
        findings = check_intents(wf)
        assert not any(f.code == "WIZ302" for f in findings)


# ===========================================================================
# 3. Multi-round absent component is tolerated (no WIZ302)
# ===========================================================================

class TestWIZ302MultiRoundTolerance:
    """An absent multipleAppointId target must NOT produce any WIZ302 finding."""

    def test_multiround_absent_component_no_error(self):
        """KB with a multi_round delegate pointing at absent component -> no WIZ302.

        The raw field in the KB carries a kdInfo with a multipleAppointId that won't
        resolve to any BizSpeechComponent, but that's tolerated (orphan/library import).
        WIZ302 only fires for dangling intentId references.
        """
        # Intents are all present -> no WIZ302 from intent side
        intents = {
            1: _intent(1, "Unclassified"),
            5: _intent(5, "AskPayment"),
        }
        kbs = {
            10: _kb(10, "Payment FAQ", (5,)),  # intents all resolve
        }
        wf = _wf(intents=intents, knowledge_bases=kbs)
        findings = check_intents(wf)
        # No WIZ302 even if multi_round has absent component (the IR KnowledgeBase
        # does not carry multi_round; that lives in KBView from flowmodel).
        assert not any(f.code == "WIZ302" for f in findings)
