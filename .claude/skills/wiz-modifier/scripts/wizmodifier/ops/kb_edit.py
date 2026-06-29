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


def _editor_value(text: str) -> dict:
    return {
        "xml": f'<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">{text}</speak>',
        "html": f"<p>{text}</p>",
        "text": text,
    }


def _find_answer_item(items: list[dict], params: dict) -> int:
    """Index into `items` of the answerType:1 item matched by `index` or `old_text`/`text`."""
    answer_idxs = [i for i, it in enumerate(items) if it.get("answerType") == 1]
    if "index" in params and params["index"] is not None:
        n = int(params["index"])
        if n < 0 or n >= len(answer_idxs):
            raise ValueError(f"answer index {n} out of range (0..{len(answer_idxs)-1})")
        return answer_idxs[n]
    text = params.get("old_text", params.get("text"))
    for i in answer_idxs:
        if items[i].get("answer") == text:
            return i
    raise ValueError(f"no answerType:1 answer matching {text!r}")


def add_kb_answer(bundle: InputBundle, params: dict, minter) -> None:
    name = params["name"]
    text = params["text"]
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    items = ed.kd_items(kb)
    new_id = str(minter.uuid(f"kb-answer:{name}:{text}"))
    new_item = {
        "afterSentence": 0, "answer": text, "answerType": 1,
        "editorValue": _editor_value(text), "id": new_id,
    }
    # insert before any trailing answerType:2 delegate item
    insert_at = len(items)
    if items and items[-1].get("answerType") == 2:
        insert_at = len(items) - 1
    items.insert(insert_at, new_item)
    ed.set_kd_items(kb, items)
    ed.sck.append({
        "branch": kb.get("branch", "dev"), "id": new_id, "isDelete": 0,
        "knowledgeId": kb["knowledgeId"],
        "knowledgeRecCutId": minter.int_id(f"kb-answer-krec:{name}:{text}"),
        "senRecName": "", "sentenceText": text, "sentenceTextUrl": "",
        "showType": 0, "speechId": kb["speechId"],
        "speechRecCutId": str(minter.uuid(f"kb-answer-srec:{name}:{text}")),
        "type": "record",
    })
    ed.flush()


def edit_kb_answer(bundle: InputBundle, params: dict, minter) -> None:
    name = params["name"]
    new_text = params["new_text"]
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    items = ed.kd_items(kb)
    idx = _find_answer_item(items, params)
    item_id = items[idx]["id"]
    items[idx]["answer"] = new_text
    items[idx]["editorValue"] = _editor_value(new_text)
    ed.set_kd_items(kb, items)
    # sync SCK row + reset audio so it re-synthesizes
    for row in ed.sck:
        if row.get("knowledgeId") == kb["knowledgeId"] and row.get("id") == item_id:
            row["sentenceText"] = new_text
            row["sentenceTextUrl"] = ""
    ed.flush()


def remove_kb_answer(bundle: InputBundle, params: dict, minter) -> None:
    name = params["name"]
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    items = ed.kd_items(kb)
    idx = _find_answer_item(items, params)
    answers = ed.answer_items(items)
    has_delegate = any(it.get("answerType") == 2 for it in items)
    if len(answers) <= 1 and not has_delegate:
        raise ValueError(f"remove-kb-answer: KB {name!r} must keep at least one response")
    item_id = items[idx]["id"]
    del items[idx]
    ed.set_kd_items(kb, items)
    ed.sck = [r for r in ed.sck
              if not (r.get("knowledgeId") == kb["knowledgeId"] and r.get("id") == item_id)]
    ed.flush()


def set_kb_multiround(bundle: InputBundle, params: dict, minter) -> None:
    """Set or remove multi-round delegation for a KB.

    params:
        name              — KB kdTitle
        target_component  — component name to delegate to; None to remove delegate
    """
    name = params["name"]
    target_component = params.get("target_component")
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    items = ed.kd_items(kb)
    old_delegate = next((it for it in items if it.get("answerType") == 2), None)

    if target_component is None:
        if old_delegate is not None:
            items = [it for it in items if it.get("answerType") != 2]
            ed.set_kd_items(kb, items)
            ed.warn(
                f"set-kb-multiround: removed delegate from KB {name!r}; old target "
                f"{old_delegate.get('multipleAppointId')!r} left as-is (category not reverted)"
            )
        ed.flush()
        return

    target = next((c for c in ed.bsc()
                   if c.get("name", "") == target_component and c.get("componentUuid")),
                  None)
    if target is None:
        raise ValueError(
            f"set-kb-multiround: target component {target_component!r} not found"
        )
    new_uuid = target["componentUuid"]
    delegate = {
        "answerType": 2,
        "editorValue": {
            "xml": '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts"></speak>',
            "html": "<p></p>",
            "text": "",
        },
        "id": str(minter.uuid(f"kb-delegate:{name}")),
        "multipleAppointId": new_uuid,
    }
    if old_delegate is not None:
        old_uuid = old_delegate.get("multipleAppointId")
        items = [it for it in items if it.get("answerType") != 2]
        if old_uuid and old_uuid != new_uuid:
            ed.warn(
                f"set-kb-multiround: retargeted KB {name!r}; old target {old_uuid!r} "
                f"left as-is (category not reverted)"
            )
    items.append(delegate)
    ed.set_kd_items(kb, items)
    target["category"] = 2
    ed.mark_bsc_dirty()
    ed.flush()


def delete_kb(bundle: InputBundle, params: dict, minter) -> None:
    """Delete a user-created knowledge base.

    Refuses to delete system/template KBs (isInit!=0) or KBs referenced by
    goto_kb nodes. Removes BizKnowledgeInfo entry and all SentenceCutKnowledge
    rows for that KB.

    params:
        name  — KB kdTitle
    """
    name = params["name"]
    ed = KbEditor(bundle, minter)
    kb = ed.find_kb(name)
    if kb.get("isInit", 0) != 0:
        raise ValueError(
            f"delete-kb: cannot delete system/template KB {name!r} (isInit="
            f"{kb.get('isInit')}); only user-generated KBs (isInit=0) are "
            f"deletable"
        )
    kid = kb["knowledgeId"]
    refs = ed.goto_kb_refs(kid)
    if refs:
        raise ValueError(
            f"delete-kb: KB {name!r} (id {kid}) is referenced by goto_kb "
            f"node(s) {refs}; rewire or delete those nodes first "
            f"(flow-mutation ops)"
        )
    delegate = next((it for it in ed.kd_items(kb)
                     if it.get("answerType") == 2), None)
    ed.bk = [k for k in ed.bk if k.get("knowledgeId") != kid]
    ed.sck = [r for r in ed.sck if r.get("knowledgeId") != kid]
    if delegate is not None and delegate.get("multipleAppointId"):
        ed.warn(
            f"delete-kb: KB {name!r} delegated to component "
            f"{delegate['multipleAppointId']!r}; left as-is "
            f"(category not reverted)"
        )
    ed.flush()
