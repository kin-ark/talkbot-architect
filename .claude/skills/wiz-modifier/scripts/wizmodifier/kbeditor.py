"""KbEditor — decode/mutate/flush the KB tables of a WIZ export.

Mirrors FlowEditor's decode→mutate→flush pattern for the KB family:
BizKnowledgeInfo (entries), SentenceCutKnowledge (per-answer audio rows),
SpeechIntent (read-only resolve), BizSpeechComponent (read-only except
multi-round category flips). kdInfo and intents are nested JSON strings
inside each BizKnowledgeInfo entry.
"""

from __future__ import annotations

import json

from wizmodifier import codec
from wizmodifier.io import InputBundle


class KbEditor:
    def __init__(self, bundle: InputBundle, minter) -> None:
        self.bundle = bundle
        self.minter = minter
        self.bk: list[dict] = codec.decode(bundle.data.get("BizKnowledgeInfo", "[]")) or []
        self.sck: list[dict] = codec.decode(bundle.data.get("SentenceCutKnowledge", "[]")) or []
        self.si: list[dict] = codec.decode(bundle.data.get("SpeechIntent", "[]")) or []
        self._bsc: list[dict] | None = None
        self._bsc_dirty = False

    # --- reads ---
    def bsc(self) -> list[dict]:
        if self._bsc is None:
            self._bsc = codec.decode(self.bundle.data.get("BizSpeechComponent", "[]")) or []
        return self._bsc

    def mark_bsc_dirty(self) -> None:
        self._bsc_dirty = True

    def find_kb(self, name: str) -> dict:
        kb = next((k for k in self.bk if k.get("kdTitle") == name), None)
        if kb is None:
            raise ValueError(f"knowledge base {name!r} not found")
        return kb

    def kd_items(self, kb: dict) -> list[dict]:
        return codec.decode(kb.get("kdInfo", "[]")) or []

    def set_kd_items(self, kb: dict, items: list[dict]) -> None:
        kb["kdInfo"] = codec.encode(items)

    @staticmethod
    def answer_items(items: list[dict]) -> list[dict]:
        """The answerType:1 (real-answer) items, excluding the answerType:2 delegate."""
        return [it for it in items if it.get("answerType") == 1]

    def sck_rows_for(self, knowledge_id) -> list[dict]:
        return [r for r in self.sck if r.get("knowledgeId") == knowledge_id]

    def intent_id_by_name(self) -> dict[str, int]:
        # Skip malformed SpeechIntent rows (missing name/id) rather than KeyError —
        # this is a general read helper that may see partial exports.
        return {
            i["intentName"]: i["intentId"]
            for i in self.si
            if i.get("intentName") is not None and i.get("intentId") is not None
        }

    def goto_kb_refs(self, knowledge_id) -> list[str]:
        """Node uuids of goto_kb (type-8) nodes whose appoint_knowledge_id == knowledge_id.

        appoint_knowledge_id is a STRING in real exports. Reads raw component details.
        details is single-JSON-encoded (a string like '{"uuid": {...}}') or "null"/absent.
        """
        target = str(knowledge_id)
        refs: list[str] = []
        for comp in self.bsc():
            raw_details = comp.get("details")
            if not raw_details or raw_details in ("null", ""):
                continue
            try:
                details = json.loads(raw_details) if isinstance(raw_details, str) else raw_details
            except (ValueError, TypeError):
                continue
            if not isinstance(details, dict):
                continue
            for node_uuid, node in details.items():
                data = node.get("data") or {}
                if node.get("type") == 8 and str(data.get("appoint_knowledge_id", "")) == target:
                    refs.append(node_uuid)
        return refs

    # --- warnings ---
    def warn(self, msg: str) -> None:
        self.bundle.warnings.append(msg)

    # --- flush ---
    def flush(self) -> None:
        self.bundle.data["BizKnowledgeInfo"] = codec.encode(self.bk)
        self.bundle.data["SentenceCutKnowledge"] = codec.encode(self.sck)
        if self._bsc_dirty and self._bsc is not None:
            self.bundle.data["BizSpeechComponent"] = codec.encode(self._bsc)
