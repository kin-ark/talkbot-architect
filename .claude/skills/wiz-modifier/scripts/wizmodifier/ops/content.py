"""Content ops: append custom variables and intents (wiz-builder shapes)."""

from __future__ import annotations

from collections.abc import Iterable

from wizmodifier import codec
from wizmodifier.io import InputBundle


def add_variable(bundle: InputBundle, params: dict, minter) -> None:
    """Append a custom variable in wiz-builder's 12-key shape (variables.py)."""
    vars_list = codec.decode(bundle.data["SpeechVariable"])
    if not vars_list:
        raise ValueError("SpeechVariable is empty; baseline must carry defaults")
    default = vars_list[0]
    vars_list.append({
        "beInit": 0,
        "branch": params.get("branch", default["branch"]),
        "createTime": 0,
        "enumVariable": 0,
        "id": minter.int_id(f"variable:{params['name']}"),
        "name": params["name"],
        "speechId": default["speechId"],
        "templateCode": default["templateCode"],
        "textType": "",
        "type": 1,
        "userId": default["userId"],
        "variableSource": 0,
    })
    bundle.data["SpeechVariable"] = codec.encode(vars_list)


def _bracket_join(items: Iterable[str], sep: str) -> str:
    """Serialise strings as '[a<sep>b]' — WIZ uses ',' for keywords, ';' for responses."""
    return "[" + sep.join(items) + "]"


def add_intent(bundle: InputBundle, params: dict, minter) -> None:
    """Append a custom intent in wiz-builder's 13-key shape (intents.py)."""
    intents = codec.decode(bundle.data["SpeechIntent"])
    if not intents:
        raise ValueError("SpeechIntent is empty; baseline must carry defaults")
    default = intents[0]
    intents.append({
        "branch": params.get("branch", default["branch"]),
        "createTime": 0,
        "intentId": minter.int_id(f"intent:{params['name']}"),
        "intentName": params["name"],
        "isDelete": 0,
        "isInit": 0,
        "keyWordInIntent": _bracket_join(params.get("keywords", []), sep=","),
        "language": params.get("language", default.get("language", 0)),
        "nodeId": "",
        "speechId": default["speechId"],
        "templateCode": default["templateCode"],
        "updateTime": 0,
        "userResponseInIntent": _bracket_join(params.get("user_responses", []), sep=";"),
    })
    bundle.data["SpeechIntent"] = codec.encode(intents)
