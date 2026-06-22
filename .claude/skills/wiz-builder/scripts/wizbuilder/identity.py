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

    Generates a fresh speechId and propagates it to every top-level field that
    contains one (both object and array fields). Replaces the single template
    BizSpeechComponent's componentUuid with a manifest-derived UUID. Updates
    branch on BizSpeechComponent. Does not modify intent language fields.
    """
    speech_id = minter.random_speech_id()

    # Propagate speechId to every top-level field that carries it.
    for key, raw in template.items():
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            decoded = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        changed = False
        if isinstance(decoded, list):
            for item in decoded:
                if isinstance(item, dict) and "speechId" in item:
                    item["speechId"] = speech_id
                    changed = True
        elif isinstance(decoded, dict) and "speechId" in decoded:
            decoded["speechId"] = speech_id
            changed = True
        if changed:
            template[key] = json.dumps(decoded, ensure_ascii=False, separators=(",", ":"))

    # Update BizSpeechComponent entries: branch + componentUuid for the (single) template entry.
    bsc_raw = template.get("BizSpeechComponent")
    if not isinstance(bsc_raw, str) or not bsc_raw.strip():
        raise ValueError(
            "apply_identity requires template['BizSpeechComponent'] to be a non-empty JSON string"
        )
    bsc = json.loads(template["BizSpeechComponent"])
    for i, comp in enumerate(bsc):
        comp["branch"] = manifest.branch
        comp["componentUuid"] = str(minter.uuid(f"component:{i}"))
        # parentUuid stays "0" (root) for template's lone component.
    template["BizSpeechComponent"] = json.dumps(bsc, ensure_ascii=False, separators=(",", ":"))

    return template
