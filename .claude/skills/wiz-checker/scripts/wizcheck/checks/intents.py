"""Intent-coverage checks (WIZ300..WIZ399)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity

_RULES_FILE = Path(__file__).resolve().parents[3] / "schema" / "intent_rules.yaml"


def _load_rules() -> dict:
    if not _RULES_FILE.exists():
        return {
            "required_intent_names": ["Unclassified"],
        }
    return yaml.safe_load(_RULES_FILE.read_text(encoding="utf-8")) or {}


_RULES = _load_rules()


def check_intents(wf: WizFile) -> list[Finding]:
    present_names = {i.name for i in wf.intents.values()}
    out: list[Finding] = []

    # WIZ301: required intents present
    for required in _RULES.get("required_intent_names", []):
        if required not in present_names:
            out.append(Finding(
                code="WIZ301",
                severity=Severity.ERROR,
                location=Location(entity="WizFile", id=None, field="SpeechIntent"),
                message=f"Required intent {required!r} is not declared.",
            ))

    # WIZ302: KB triggering intents declared in SpeechIntent
    for kb in wf.knowledge_bases.values():
        for iid in kb.intents:
            if iid not in wf.intents:
                out.append(Finding(
                    code="WIZ302",
                    severity=Severity.ERROR,
                    location=Location(
                        entity="BizKnowledgeInfo",
                        id=str(kb.knowledge_id),
                        field="intents",
                    ),
                    message=(
                        f"Knowledge base {kb.title!r} (id {kb.knowledge_id}) references"
                        f" intent id {iid} which is not declared in SpeechIntent."
                    ),
                ))

    # WIZ303: goto_kb node targets a knowledgeId not present in BizKnowledgeInfo.
    # WARNING, not ERROR: an absent KB id may be a legitimate library/external KB
    # reference (the shipped goto_kb tolerance), so it imports fine — but a dangling
    # in-export jump is a deploy concern. It is in DEPLOY_BLOCKER_CODES, so --deploy
    # / --strict flag it while a plain check tolerates it.
    if wf.flow_model is not None:
        known_kb_ids = set(wf.knowledge_bases.keys())
        for comp in wf.flow_model.components:
            for node in comp.nodes.values():
                if node.node_type != "goto_kb":
                    continue
                for branch in node.branches:
                    tgt = branch.target_kb
                    if tgt is not None and tgt not in known_kb_ids:
                        out.append(Finding(
                            code="WIZ303",
                            severity=Severity.WARNING,
                            location=Location(
                                entity="FlowNode",
                                id=node.uuid,
                                field=None,
                            ),
                            message=(
                                f"goto_kb node {node.uuid!r} targets knowledgeId {tgt} "
                                f"which is not present in BizKnowledgeInfo (dangling KB jump "
                                f"or external/library KB)."
                            ),
                        ))

    # WIZ304: a user-created (isInit=0), non-deleted KB with no Default Response
    # (no non-empty Single-Sentence answer AND no Multi-Round delegate) is incomplete.
    # System KBs (isInit=1, e.g. background/monitor KBs) are legitimately empty -> exempt.
    for kb in wf.knowledge_bases.values():
        raw = getattr(kb, "raw", {}) or {}
        if raw.get("isInit", 0) != 0 or raw.get("isDelete", 0) != 0:
            continue
        kd = raw.get("kdInfo", "[]")
        try:
            items = json.loads(kd) if isinstance(kd, str) else (kd or [])
        except (ValueError, TypeError):
            continue  # malformed kdInfo — never crash the checker; other checks may flag it
        if not isinstance(items, list):
            continue
        has_answer = any(
            it.get("answerType") == 1 and (it.get("answer") or "").strip() for it in items
        )
        has_delegate = any(it.get("answerType") == 2 for it in items)
        if not has_answer and not has_delegate:
            out.append(Finding(
                code="WIZ304",
                severity=Severity.WARNING,
                location=Location(
                    entity="BizKnowledgeInfo",
                    id=str(kb.knowledge_id),
                    field="kdInfo"
                ),
                message=(
                    f"Knowledge base {kb.title!r} (id {kb.knowledge_id}) has no Default Response "
                    f"(no Single-Sentence answer and no Multi-Round delegate) — incomplete."
                ),
            ))

    return out
