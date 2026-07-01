"""apply_hotwords: emit a global BizNodeHotWords row from manifest.hot_words."""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Manifest


def apply_hotwords(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
) -> dict[str, Any]:
    """Append a global BizNodeHotWords row from manifest.hot_words.

    If no hot_words are present, returns the template unchanged.
    Otherwise appends one row to BizNodeHotWords with empty nodeId (global scope),
    hotWords as a comma-joined string, and constants sourced from SpeechIntent[0].
    """
    words = [w for w in getattr(manifest, "hot_words", ()) if w and w.strip()]
    if not words:
        return template

    intents = json.loads(template.get("SpeechIntent", "[]"))
    base = intents[0] if intents else {}
    speech_id = base.get("speechId", 0)
    template_code = base.get("templateCode", "")

    rows_raw = template.get("BizNodeHotWords", "[]")
    rows = json.loads(rows_raw) if isinstance(rows_raw, str) else (rows_raw or [])

    rows.append({
        "branch": base.get("branch", "dev"),
        "createId": 0,
        "createTime": 0,
        "engineType": "3",
        "hotWords": ",".join(w.strip() for w in words),
        "hotWordsIndustryId": 0,
        "id": minter.int_id("hotwords:global"),
        "isDelete": 0,
        "modifyId": 0,
        "modifyTime": 0,
        "nodeId": "",
        "speechId": speech_id,
        "status": 2,
        "templateCode": template_code,
    })

    template["BizNodeHotWords"] = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return template
