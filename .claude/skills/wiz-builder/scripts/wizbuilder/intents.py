"""apply_intents: append manifest custom_intents to the template's SpeechIntent list."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Manifest


def _bracket_join(items: Iterable[str]) -> str:
    """Serialise an iterable of strings as '[a;b;c]' (or '[]' if empty).

    Matches the on-the-wire format observed in real WIZ.AI exports
    (talkbot/TSP+Matchmaking) for keyWordInIntent / userResponseInIntent.
    """
    return "[" + ";".join(items) + "]"


def apply_intents(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
) -> dict[str, Any]:
    """Append custom_intents to the template's SpeechIntent list.

    Custom intents mirror the 11-key shape of the Empty+Dialogue defaults,
    plus keyWordInIntent and userResponseInIntent as bracket-strings.
    templateCode and speechId are inherited from the existing defaults;
    createTime and updateTime are 0 to keep builds deterministic.
    """
    raw = template.get("SpeechIntent")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            "apply_intents requires template['SpeechIntent'] to be a non-empty JSON string"
        )
    intents = json.loads(raw)
    if not intents:
        raise ValueError(
            "apply_intents: template['SpeechIntent'] decoded to an empty list; "
            "Empty+Dialogue baseline must carry default intents"
        )

    default = intents[0]
    speech_id = default["speechId"]
    template_code = default["templateCode"]

    for ci in manifest.custom_intents:
        intents.append({
            "branch": manifest.branch,
            "createTime": 0,
            "intentId": minter.int_id(f"intent:{ci.name}"),
            "intentName": ci.name,
            "isDelete": 0,
            "isInit": 0,
            "keyWordInIntent": _bracket_join(ci.keywords),
            "language": ci.language,
            "nodeId": "",
            "speechId": speech_id,
            "templateCode": template_code,
            "updateTime": 0,
            "userResponseInIntent": _bracket_join(ci.user_responses),
        })

    template["SpeechIntent"] = json.dumps(intents, ensure_ascii=False)
    return template
