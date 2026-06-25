"""apply_knowledge_bases: emit BizKnowledgeInfo entries + SentenceCutKnowledge rows.

Clones config fields verbatim from the baseline template's first KB entry,
then parameterises kdTitle, intents, kdInfo, knowledgeId, and speechId per
manifest KnowledgeBase.

Ground truth: knowledgeId 179824 from
  talkbot/Tiktok+Paylater+DPD0/speech4892384019254584542.json
"""

from __future__ import annotations

import json
from typing import Any

from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Manifest
from wizbuilder.noderender import _wide_int


def apply_knowledge_bases(
    template: dict[str, Any],
    manifest: Manifest,
    minter: IdMinter,
    *,
    kb_id_by_name: dict[str, int],
    canvas_uuid_by_name: dict[str, str],
) -> dict[str, Any]:
    """Append manifest knowledge_bases to the template's BizKnowledgeInfo and
    SentenceCutKnowledge lists.

    Parameters
    ----------
    template:
        The in-progress speech export dict (already passed through apply_canvases).
    manifest:
        The parsed manifest; manifest.knowledge_bases drives emission.
    minter:
        Deterministic ID minter (manifest-hash-seeded).
    kb_id_by_name:
        Pre-minted {kb.name: knowledgeId} map built by compile.py before canvases
        are rendered, so talk nodes can reference KB ids in allow_jump_knowledges.
    canvas_uuid_by_name:
        Name→componentUuid map built by apply_canvases.  Reserved for Task 3
        (multi-round linkage); not used by simple-KB emission in this task.
    """
    if not manifest.knowledge_bases:
        return template

    # --- resolve merged SpeechIntent (baseline + custom) ---
    speech_intents_raw = template.get("SpeechIntent", "[]")
    speech_intents: list[dict] = (
        json.loads(speech_intents_raw)
        if isinstance(speech_intents_raw, str)
        else speech_intents_raw
    )
    intent_id_by_name: dict[str, int] = {
        i["intentName"]: i["intentId"] for i in speech_intents
    }

    # --- clone config constants from the baseline's first KB entry ---
    bk_raw = template.get("BizKnowledgeInfo", "[]")
    bk_list: list[dict] = json.loads(bk_raw) if isinstance(bk_raw, str) else bk_raw
    if not bk_list:
        raise ValueError(
            "apply_knowledge_bases: template['BizKnowledgeInfo'] is empty; "
            "Empty+Dialogue baseline must carry default KB entries to clone config from"
        )
    base_kb = bk_list[0]

    speech_id: int = base_kb["speechId"]
    create_id: int = base_kb["createId"]
    create_time: int = base_kb["createTime"]
    modify_id: int = base_kb["modifyId"]
    modify_time: int = base_kb["modifyTime"]
    exclusive_key_words: str = base_kb["exclusiveKeyWords"]

    # --- decode existing SentenceCutKnowledge (append; don't replace) ---
    sck_raw = template.get("SentenceCutKnowledge", "[]")
    sck_list: list[dict] = json.loads(sck_raw) if isinstance(sck_raw, str) else sck_raw

    # --- emit one BizKnowledgeInfo + SCK rows per manifest KB ---
    for kb in manifest.knowledge_bases:
        if kb.multi_round is not None:
            # Task 3: multi-round linkage deferred.
            continue

        knowledge_id: int = kb_id_by_name[kb.name]

        # Resolve intents → [{intentName, intentId}]
        resolved_intents: list[dict] = []
        for intent_name in kb.intents:
            if intent_name not in intent_id_by_name:
                raise ValueError(
                    f"apply_knowledge_bases: KB {kb.name!r} references intent "
                    f"{intent_name!r} which is not in the merged SpeechIntent list; "
                    f"ensure it is declared as a custom_intent in the manifest"
                )
            resolved_intents.append({
                "intentName": intent_name,
                "intentId": intent_id_by_name[intent_name],
            })

        # Build kdInfo items (one per answer text)
        kd_info_items: list[dict] = []
        for ai, answer_text in enumerate(kb.answers):
            item_id = str(_wide_int(f"{minter.manifest_hash}:kdinfo:{kb.name}:{ai}"))
            kd_info_items.append({
                "afterSentence": 0,
                "answer": answer_text,
                "answerType": 1,
                "editorValue": {
                    "xml": (
                        '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts">'
                        f"{answer_text}"
                        "</speak>"
                    ),
                    "html": f"<p>{answer_text}</p>",
                    "text": answer_text,
                },
                "id": item_id,
            })

        bk_entry: dict = {
            "allowInterrupt": 1,
            "answerType": 1,
            "branch": manifest.branch,
            "canInterruptPercent": 80.0,
            "conditions": json.dumps([{"type": 0}], ensure_ascii=False, separators=(", ", ": ")),
            "createId": create_id,
            "createTime": create_time,
            "enableUse": 1,
            "engineType": "3",
            "exclusiveKeyWords": exclusive_key_words,
            "forceHangup": 0,
            "intentionJudgmentTime": 2.0,
            "intents": json.dumps(resolved_intents, ensure_ascii=False, separators=(",", ":")),
            "interruptRecognitionThresholdSwitch": 0,
            "isDelete": 0,
            "isInit": 0,
            "isTransfer": 0,
            "kdInfo": json.dumps(kd_info_items, ensure_ascii=False, separators=(",", ":")),
            "kdTitle": kb.name,
            "kdType": 0,
            "knowledgeId": knowledge_id,
            "modifyId": modify_id,
            "modifyTime": modify_time,
            "nodeResponseDurationSwitch": 0,
            "noticeSendType": 0,
            "recordNum": 0,
            "soundexMatch": 0,
            "speakType": 1,
            "speechId": speech_id,
            "threshold": "",
            "valueAssignment": "[]",
            "wordNum": 0,
        }
        bk_list.append(bk_entry)

        # Emit one SentenceCutKnowledge row per answer
        for ai, answer_text in enumerate(kb.answers):
            # Re-use the same kdInfo item id as the SCK row id (mirrors WIZ.AI export pattern)
            item_id = str(_wide_int(f"{minter.manifest_hash}:kdinfo:{kb.name}:{ai}"))
            krec_cut_id: int = minter.int_id(f"sck-knowledgeRecCutId:{kb.name}:{ai}")
            speech_rec_cut_id = str(
                _wide_int(f"{minter.manifest_hash}:sck-speechRecCutId:{kb.name}:{ai}")
            )
            sck_row: dict = {
                "branch": "dev",
                "id": item_id,
                "isDelete": 0,
                "knowledgeId": knowledge_id,
                "knowledgeRecCutId": krec_cut_id,
                "senRecName": "",
                "sentenceText": answer_text,
                "sentenceTextUrl": "",
                "showType": 0,
                "speechId": speech_id,
                "speechRecCutId": speech_rec_cut_id,
                "type": "record",
            }
            sck_list.append(sck_row)

    template["BizKnowledgeInfo"] = json.dumps(
        bk_list, ensure_ascii=False, separators=(",", ":")
    )
    template["SentenceCutKnowledge"] = json.dumps(
        sck_list, ensure_ascii=False, separators=(",", ":")
    )
    return template
