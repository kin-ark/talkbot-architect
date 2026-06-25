"""apply_knowledge_bases: emit BizKnowledgeInfo entries + SentenceCutKnowledge rows.

Clones the FULL field set from the baseline template's first KB entry (ground truth:
knowledgeId 179824 in talkbot/Tiktok+Paylater+DPD0/speech4892384019254584542.json),
then overrides only the variable fields: kdTitle, intents, kdInfo, knowledgeId,
speechId.  Instance/stat fields are reset to new-KB values.

BizKnowledgeInfo full field set (35 fields — all must be present):
  allowInterrupt, answerType, branch, canInterruptPercent, conditions, createId,
  createTime, enableUse, engineType, exclusiveKeyWords, forceHangup,
  intentionJudgmentTime, intents, interruptRecognitionThresholdSwitch, isDelete,
  isInit, isTransfer, kdInfo, kdTitle, kdType, knowledgeId, modifyId, modifyTime,
  nodeResponseDurationSwitch, noticeSendType, recordNum, repeatScriptType,
  soundexMatch, speakType, speechId, tagList, threshold, valueAssignment, wordNum.

Previously missing (added in KB-T2 fix): repeatScriptType, tagList.

SentenceCutKnowledge speechRecCutId: UUID-format string (deterministic uuid5 via
IdMinter.uuid), NOT a wide-int.  knowledgeRecCutId stays int (matches real rows).

Multi-round KBs (kb.multi_round is not None):
  The final kdInfo item (appended after all normal answerType:1 items) has:
    answerType: 2
    multipleAppointId: <target canvas componentUuid>
    editorValue: {xml: '<speak …></speak>', html: '<p></p>', text: ''}  [empty body]
    id: <UUID-format string, minted via minter.uuid>
  The KB top-level answerType stays 1.
  The delegating item's editorValue is always the empty-body form — decoded from
  knowledgeId 179837 in speech4892384019254584542.json (golden reference).
  SentenceCutKnowledge rows are only emitted for normal (answerType:1) items.
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

        # Multi-round: append the delegating answerType:2 item LAST.
        # Shape decoded from golden KB 179837 (speech4892384019254584542.json):
        #   {answerType:2, multipleAppointId:<componentUuid>, editorValue:{empty}, id:<uuid>}
        # editorValue is always the empty-body form: xml="<speak …></speak>", html="<p></p>",
        # text="" — regardless of whether normal answers precede it.
        if kb.multi_round is not None:
            target_uuid = canvas_uuid_by_name.get(kb.multi_round)
            if target_uuid is None:
                raise ValueError(
                    f"apply_knowledge_bases: KB {kb.name!r} multi_round target "
                    f"{kb.multi_round!r} not found in canvas_uuid_by_name; "
                    f"ensure the canvas is declared in the manifest"
                )
            delegate_item_id = str(minter.uuid(f"kdinfo-delegate:{kb.name}"))
            kd_info_items.append({
                "answerType": 2,
                "editorValue": {
                    "xml": '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts"></speak>',
                    "html": "<p></p>",
                    "text": "",
                },
                "id": delegate_item_id,
                "multipleAppointId": target_uuid,
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
            "isInit": 0,  # 0 = user-created; template runtime KB has isInit:1
            "isTransfer": 0,
            "kdInfo": json.dumps(kd_info_items, ensure_ascii=False, separators=(",", ":")),
            "kdTitle": kb.name,
            "kdType": 0,
            "knowledgeId": knowledge_id,
            "modifyId": modify_id,
            "modifyTime": modify_time,
            # nodeResponseDurationSwitch: cloned from base_kb if present; falls back to 0.
            # The Empty+Dialogue baseline has this field; real deploy-verified KBs do too.
            "nodeResponseDurationSwitch": base_kb.get("nodeResponseDurationSwitch", 0),
            "noticeSendType": 0,
            "recordNum": 0,  # reset stat: no recordings yet
            # repeatScriptType: ground-truth value from knowledgeId 179824 (deploy-verified).
            # The Empty+Dialogue baseline omits this field; cloning from ground truth is safe.
            "repeatScriptType": 1,
            "soundexMatch": 0,
            "speakType": 1,
            "speechId": speech_id,
            "tagList": "[]",  # fresh KB: no tags; template uses a JSON-string-encoded list
            "threshold": "",
            "valueAssignment": "[]",
            "wordNum": 0,  # reset stat: no word count yet
        }
        bk_list.append(bk_entry)

        # Emit one SentenceCutKnowledge row per answer.
        # Field types must match real rows (ground truth: knowledgeId 179824):
        #   id: str (wide-int string)     knowledgeRecCutId: int
        #   speechRecCutId: str (UUID4-format, e.g. "781f1a53-0d7b-4d88-...")
        for ai, answer_text in enumerate(kb.answers):
            # Re-use the same kdInfo item id as the SCK row id (mirrors WIZ.AI export pattern)
            item_id = str(_wide_int(f"{minter.manifest_hash}:kdinfo:{kb.name}:{ai}"))
            krec_cut_id: int = minter.int_id(f"sck-knowledgeRecCutId:{kb.name}:{ai}")
            # speechRecCutId must be a UUID-format string (not a wide-int).
            # Real rows: "781f1a53-0d7b-4d88-a34c-49e1000fba38" etc.
            speech_rec_cut_id: str = str(minter.uuid(f"sck-speechRecCutId:{kb.name}:{ai}"))
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
