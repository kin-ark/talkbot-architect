"""apply_identity: set name, branch, language, speechId, componentUuid on the parsed template."""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Manifest


def apply_identity(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
) -> dict[str, Any]:
    """Mutate the parsed template in place to reflect the manifest's identity fields.

    Sets a fresh speechId across all string-encoded top-level lists that carry it
    (BizSpeechComponent, SpeechIntent, SpeechVariable, etc.). Replaces the single
    template BizSpeechComponent's componentUuid with a manifest-derived UUID.
    Updates branch on BizSpeechComponent. Does not modify intent language fields.
    """
    speech_id = minter.random_speech_id()

    # Top-level string-encoded lists that carry speechId on their items.
    for key in (
        "BizSpeechComponent",
        "SpeechVariable",
        "SpeechIntent",
        "SentenceCutSpeech",
        "SpeechAudio",
    ):
        raw = template.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        items = json.loads(raw)
        for item in items:
            if "speechId" in item:
                item["speechId"] = speech_id
        template[key] = json.dumps(items, ensure_ascii=False)

    # Update BizSpeechComponent entries: branch + componentUuid for the (single) template entry.
    bsc = json.loads(template["BizSpeechComponent"])
    for i, comp in enumerate(bsc):
        comp["branch"] = manifest.branch
        comp["componentUuid"] = str(minter.uuid(f"component:{i}"))
        # parentUuid stays "0" (root) for template's lone component.
    template["BizSpeechComponent"] = json.dumps(bsc, ensure_ascii=False)

    return template
