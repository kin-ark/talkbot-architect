"""Content ops: append custom variables and intents (wiz-builder shapes)."""

# NOTE: The 12-key variable and 13-key intent shapes are reproduced from
# wiz-builder (variables.py / intents.py), the canonical shape-of-record.
# branch/language fall back to the loaded file's first default entry when a
# param is omitted (a modifier inherits the export's existing values), which
# differs intentionally from wiz-builder's Manifest-sourced values.

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from wizfacts import load_facts

from wizmodifier import codec
from wizmodifier.io import InputBundle


@lru_cache(maxsize=1)
def _supported_langs() -> frozenset[str]:
    return frozenset(load_facts().get("lang.supported"))


def _check_language(value) -> None:
    """Reject a string language not in the documented supported set.

    Only strings are checked; a non-string (e.g. the defensive int-0 default)
    passes through unchanged because it is not an author-supplied ISO code.
    """
    if isinstance(value, str) and value.strip():
        supported = _supported_langs()
        if value not in supported:
            raise ValueError(
                f"add-intent/add-variable: language {value!r} is not a documented "
                f"supported language ({sorted(supported)})"
            )


def add_variable(bundle: InputBundle, params: dict, minter) -> None:
    """Append a custom variable in wiz-builder's 12-key shape (variables.py)."""
    name = params["name"]
    vars_list = codec.decode(bundle.data["SpeechVariable"])
    if not vars_list:
        raise ValueError("SpeechVariable is empty; baseline must carry defaults")
    # Duplicate name -> WIZ import error SPEECH-0230. Fail loudly (the dashboard surfaces
    # the ValueError as an error proposal) rather than silently dropping the add.
    if any(v.get("name") == name for v in vars_list):
        raise ValueError(f"add-variable: variable {name!r} already exists")
    default = vars_list[0]
    _check_language(params.get("language"))
    vars_list.append({
        "beInit": 0,
        "branch": params.get("branch", default["branch"]),
        "createTime": 0,
        "enumVariable": 0,
        "id": minter.int_id(f"variable:{name}"),
        "name": name,
        "speechId": default["speechId"],
        "templateCode": default["templateCode"],
        # "DEFAULT" is the deploy-valid textType (empty string "" is rejected at deploy).
        "textType": "DEFAULT",
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
    _check_language(params.get("language"))
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
