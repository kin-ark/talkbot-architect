"""apply_variables: append manifest custom_variables to the template's SpeechVariable list."""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Manifest


def apply_variables(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
) -> dict[str, Any]:
    """Append custom_variables to the template's SpeechVariable list.

    Custom variables get variableSource=0 (user-authored), textType empty string, and
    a deterministic int id derived from the manifest hash + variable name.
    Inherits speechId from the existing default variables (single talkbot).
    """
    vars_list = json.loads(template["SpeechVariable"])
    # Empty+Dialogue always has 9 defaults; fall back to 0 only if something is wrong upstream.
    speech_id = vars_list[0]["speechId"] if vars_list else 0

    for cv in manifest.custom_variables:
        vars_list.append({
            "id": minter.int_id(f"variable:{cv.name}"),
            "name": cv.name,
            "textType": "",
            "type": 0,
            "variableSource": 0,
            "speechId": speech_id,
            "branch": manifest.branch,
        })

    template["SpeechVariable"] = json.dumps(vars_list, ensure_ascii=False)
    return template
