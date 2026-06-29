"""In-place KB edit ops (rename, intents, answers, multi-round, delete)."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.kbeditor import KbEditor


def rename_kb(bundle: InputBundle, params: dict, minter) -> None:
    """Rename a knowledge base.

    params:
        name      — current KB kdTitle
        new_name  — new KB kdTitle; must not already exist in BizKnowledgeInfo
    """
    name = params["name"]
    new_name = params["new_name"]
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    if new_name != name and any(k.get("kdTitle") == new_name for k in ed.bk):
        raise ValueError(f"rename-kb: knowledge base {new_name!r} already exists")
    kb["kdTitle"] = new_name
    ed.flush()


def set_kb_intents(bundle: InputBundle, params: dict, minter) -> None:
    """Set intents for a knowledge base, resolving intent names to IDs.

    params:
        name    — KB kdTitle
        intents — list of intent names (strings); each must exist in SpeechIntent
    """
    name = params["name"]
    intent_names = list(params.get("intents") or [])
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    by_name = ed.intent_id_by_name()
    resolved = []
    for n in intent_names:
        if n not in by_name:
            raise ValueError(
                f"set-kb-intents: KB {name!r} references intent {n!r} not in SpeechIntent"
            )
        resolved.append({"intentName": n, "intentId": by_name[n]})
    kb["intents"] = codec.encode(resolved)
    ed.flush()
