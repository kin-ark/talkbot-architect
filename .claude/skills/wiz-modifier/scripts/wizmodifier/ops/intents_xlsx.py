"""import-intents-xlsx: ingest a WIZ intent Excel into an existing export.

Groups rows by intent name; composes add_intent / set_intent_training.
Keyword -> keywords, User response -> user_responses. Include/Exclude have
no full-export home (advanced rules) -> warned + skipped.
"""

from __future__ import annotations

import json

from wizmodifier.io import InputBundle
from wizmodifier.ops.content import add_intent, set_intent_training

_LANG_DISPLAY_TO_CODE = {
    "bahasa indonesia": "IDN", "indonesian": "IDN",
    "english": "ENG",
    "chinese": "ZHO", "中文": "ZHO",
    "thai": "THA",
}
_LANG_CODE_TO_DISPLAY = {
    "IDN": "Bahasa Indonesia", "ENG": "English", "ZHO": "Chinese", "THA": "Thai",
}


def _unbracket(value: str, sep: str) -> list[str]:
    """Inverse of bracket syntax: '[a<sep>b]' -> ['a','b']. Tolerant of empty/[]."""
    s = (value or "").strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return [p for p in s.split(sep) if p != ""] if s else []


def _lang_code(display: str, warnings: list[str]) -> str:
    code = _LANG_DISPLAY_TO_CODE.get((display or "").strip().lower())
    if code is None:
        warnings.append(f"import-intents-xlsx: unknown language {display!r}, defaulting to IDN")
        return "IDN"
    return code


def _header_index(rows: list[list]) -> tuple[int, dict[str, int]]:
    """Find the header row (has Intent/Type/Content) and column indices."""
    for i, row in enumerate(rows):
        cells = [str(c).strip().lower() if c is not None else "" for c in row]
        if "intent" in cells and "type" in cells and "content" in cells:
            idx = {name: cells.index(name) for name in ("intent", "type", "content")}
            idx["language"] = cells.index("language") if "language" in cells else -1
            return i, idx
    raise ValueError("import-intents-xlsx: sheet missing Intent/Type/Content header")


def import_intents_xlsx(bundle: InputBundle, params: dict, minter) -> None:
    from wizmodifier.xlsx import read_rows
    path = params.get("path")
    if not path:
        raise ValueError("import-intents-xlsx: 'path' required")
    rows = read_rows(path)
    if not rows:
        raise ValueError("import-intents-xlsx: empty sheet")
    hdr_i, col = _header_index(rows)

    def get_cell(row: list, col_idx: int) -> str:
        """Extract a cell value from a row, handling None and missing columns."""
        return (
            "" if col_idx < 0 or col_idx >= len(row) or row[col_idx] is None
            else str(row[col_idx]).strip()
        )

    # group by intent name (preserve first-seen order)
    grouped: dict[str, dict] = {}
    order: list[str] = []
    skipped_adv = 0
    for row in rows[hdr_i + 1:]:
        name = get_cell(row, col["intent"])
        typ = get_cell(row, col["type"]).lower()
        content = get_cell(row, col["content"])
        if not name or not content:
            continue
        g = grouped.get(name)
        if g is None:
            g = {
                "keywords": [],
                "user_responses": [],
                "language": "",
            }
            grouped[name] = g
            order.append(name)
        # Capture language as first non-empty value across the group's rows
        if not g["language"]:
            lang_cell = get_cell(row, col["language"])
            if lang_cell:
                g["language"] = lang_cell
        if typ == "keyword":
            g["keywords"].append(content)
        elif typ in ("user response", "user_response"):
            g["user_responses"].append(content)
        elif typ in ("include", "exclude"):
            skipped_adv += 1
        else:
            msg = (
                f"import-intents-xlsx: unknown Type {typ!r} on intent {name!r}, "
                "skipped"
            )
            bundle.warnings.append(msg)

    if skipped_adv:
        bundle.warnings.append(
            f"import-intents-xlsx: skipped {skipped_adv} Include/Exclude row(s) "
            f"(advanced rules have no full-export representation)")

    # Skip intents with no keywords and no user_responses (no NLU signal)
    skipped_empty = []
    for name in order:
        g = grouped[name]
        if not g["keywords"] and not g["user_responses"]:
            skipped_empty.append(name)
            bundle.warnings.append(
                f"import-intents-xlsx: intent {name!r} has no Keyword/User-response rows, skipped"
            )
    for name in skipped_empty:
        del grouped[name]
    order = [n for n in order if n in grouped]

    existing = {i.get("intentName") for i in json.loads(bundle.data.get("SpeechIntent", "[]"))}
    for name in order:
        g = grouped[name]
        if name in existing:
            set_intent_training(
                bundle, {"name": name, "keywords": g["keywords"],
                         "user_responses": g["user_responses"]}, minter)
        else:
            add_intent(
                bundle, {"name": name, "keywords": g["keywords"],
                         "user_responses": g["user_responses"],
                         "language": _lang_code(g["language"], bundle.warnings)}, minter)


def intent_export_rows(speech_intent: list) -> list[list]:
    """Export user intents (isInit==1) as rows for Excel output.

    For each user intent, emit one row per keyword and one per user_response.
    Row format: [intentName, type, content, languageDisplay]
    System intents (isInit==0) are skipped.
    Returns DATA rows only (no header/note).
    """
    rows = []
    for intent in speech_intent:
        if intent.get("isInit") != 1:  # Skip system intents (isInit==0)
            continue
        name = intent.get("intentName", "")
        lang = str(intent.get("language", "IDN"))
        disp = _LANG_CODE_TO_DISPLAY.get(lang, lang)
        for kw in _unbracket(intent.get("keyWordInIntent", ""), ","):
            rows.append([name, "Keyword", kw, disp])
        for ur in _unbracket(intent.get("userResponseInIntent", ""), ";"):
            rows.append([name, "User response", ur, disp])
    return rows
