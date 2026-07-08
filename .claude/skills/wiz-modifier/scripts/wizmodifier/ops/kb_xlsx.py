"""import-kb-xlsx: ingest a WIZ KB Excel (Title|Intent|Dialogue Content) into an export.

One row = one KB. Trigger intent resolved by name against SpeechIntent
(absent -> warn+skip). Composes add_kb (new) / set_kb_intents + edit/add_kb_answer
(existing). Content is a single bracket-wrapped answer.
"""

from __future__ import annotations

import json

from wizmodifier.io import InputBundle
from wizmodifier.ops.content import add_kb
from wizmodifier.ops.kb_edit import add_kb_answer, edit_kb_answer, set_kb_intents


def _strip_brackets(s: str) -> str:
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith("[") and s.endswith("]"):
        return s[1:-1]
    return s


def _unbracket(value: str, sep: str) -> list[str]:
    """Inverse of bracket syntax: '[a<sep>b]' -> ['a','b']. Tolerant of empty/[]."""
    s = (value or "").strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return [p for p in s.split(sep) if p != ""] if s else []


def _header_index(rows: list[list]) -> tuple[int, dict[str, int]]:
    for i, row in enumerate(rows):
        cells = [str(c).strip().lower() if c is not None else "" for c in row]
        if "title" in cells and "intent" in cells and "dialogue content" in cells:
            return i, {
                "title": cells.index("title"),
                "intent": cells.index("intent"),
                "content": cells.index("dialogue content"),
            }
    raise ValueError("import-kb-xlsx: sheet missing Title/Intent/Dialogue Content header")


def _kb_answer_count(bundle: InputBundle, title: str) -> int:
    bk = json.loads(bundle.data.get("BizKnowledgeInfo", "[]"))
    kb = next((k for k in bk if k.get("kdTitle") == title), None)
    if kb is None:
        return 0
    info = kb.get("kdInfo")
    info = json.loads(info) if isinstance(info, str) else (info or [])
    return sum(1 for it in info if isinstance(it, dict) and it.get("answerType") == 1)


def import_kb_xlsx(bundle: InputBundle, params: dict, minter) -> None:
    from wizmodifier.xlsx import read_rows
    path = params.get("path")
    if not path:
        raise ValueError("import-kb-xlsx: 'path' required")
    rows = read_rows(path)
    if not rows:
        raise ValueError("import-kb-xlsx: empty sheet")
    hdr_i, col = _header_index(rows)

    seen: set[str] = set()
    for row in rows[hdr_i + 1:]:
        def cell(name, r):
            j = col[name]
            if j >= len(r) or r[j] is None:
                return ""
            return str(r[j]).strip()

        title = cell("title", row)
        intent = cell("intent", row)
        answer = _strip_brackets(cell("content", row))
        if not title or not answer:
            continue
        if title in seen:
            bundle.warnings.append(f"import-kb-xlsx: duplicate Title {title!r} in sheet, skipped")
            continue
        seen.add(title)

        si_json = bundle.data.get("SpeechIntent", "[]")
        intent_names = {i.get("intentName") for i in json.loads(si_json)}
        if intent not in intent_names:
            bundle.warnings.append(
                f"import-kb-xlsx: KB {title!r} trigger intent {intent!r} not in "
                f"SpeechIntent, skipped (import the intent Excel first)")
            continue

        bk_json = bundle.data.get("BizKnowledgeInfo", "[]")
        existing = {k.get("kdTitle") for k in json.loads(bk_json)}
        if title in existing:
            set_kb_intents(bundle, {"name": title, "intents": [intent]}, minter)
            if _kb_answer_count(bundle, title) > 0:
                edit_kb_answer(bundle, {"name": title, "new_text": answer, "index": 0}, minter)
            else:
                add_kb_answer(bundle, {"name": title, "text": answer}, minter)
        else:
            add_kb(bundle, {"name": title, "intents": [intent], "answers": [answer]}, minter)


def kb_export_rows(biz_kb: list, speech_intent: list) -> list[list]:
    """Export user KBs (isInit==0) as rows for Excel output.

    For each user KB with at least one answerType==1 answer, emit one row:
    [kdTitle, firstIntentName, "[" + firstAnswer + "]"]
    System KBs (isInit==1) are skipped.
    Returns DATA rows only (no header/note).
    """
    rows = []
    # Build intent id -> name map for lookups
    intent_by_id = {i.get("intentId"): i.get("intentName") for i in speech_intent}
    for kb in biz_kb:
        if kb.get("isInit") != 0:  # Skip system KBs (isInit==1)
            continue
        # Extract answers from kdInfo
        info = kb.get("kdInfo")
        info = json.loads(info) if isinstance(info, str) else (info or [])
        answers = [it.get("answer") for it in info
                   if isinstance(it, dict) and it.get("answerType") == 1 and it.get("answer")]
        if not answers:
            continue  # Skip KBs with no single-sentence answers
        # Extract first intent name
        intents = kb.get("intents")
        intents = json.loads(intents) if isinstance(intents, str) else (intents or [])
        intent_name = ""
        if intents:
            first = intents[0]
            intent_name = first.get("intentName") or intent_by_id.get(first.get("intentId"), "")
        rows.append([kb.get("kdTitle", ""), intent_name, f"[{answers[0]}]"])
    return rows
