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

    Custom variables mirror the 12-key shape of the existing default platform
    variables, with variableSource=0 (user-authored), type=1 (custom string),
    textType empty string, and createTime=0 to keep builds deterministic.
    templateCode, userId, and speechId are inherited from the existing
    defaults so customs and defaults belong to the same speech bundle.
    """
    raw = template.get("SpeechVariable")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            "apply_variables requires template['SpeechVariable'] to be a non-empty JSON string"
        )
    vars_list = json.loads(raw)
    if not vars_list:
        raise ValueError(
            "apply_variables: template['SpeechVariable'] decoded to an empty list; "
            "Empty+Dialogue baseline must carry default platform variables"
        )

    default = vars_list[0]
    speech_id = default["speechId"]
    template_code = default["templateCode"]
    user_id = default["userId"]

    for cv in manifest.custom_variables:
        vars_list.append({
            "beInit": 0,
            "branch": manifest.branch,
            "createTime": 0,
            "enumVariable": 0,
            "id": minter.int_id(f"variable:{cv.name}"),
            "name": cv.name,
            "speechId": speech_id,
            "templateCode": template_code,
            "textType": "",
            "type": 1,
            "userId": user_id,
            "variableSource": 0,
        })

    template["SpeechVariable"] = json.dumps(vars_list, ensure_ascii=False, separators=(",", ":"))
    return template
