"""Content ops: append custom variables, intents, and knowledge bases (wiz-builder shapes)."""

# NOTE: The 12-key variable and 13-key intent shapes are reproduced from
# wiz-builder (variables.py / intents.py), the canonical shape-of-record.
# branch/language fall back to the loaded file's first default entry when a
# param is omitted (a modifier inherits the export's existing values), which
# differs intentionally from wiz-builder's Manifest-sourced values.
#
# The add_kb BizKnowledgeInfo field set mirrors wizbuilder/knowledge.py
# (apply_knowledge_bases) — that file is the shape-of-record for KBs.
# We duplicate rather than import because knowledge.py expects a Manifest
# object and a pre-built kb_id_by_name map; the modifier supplies looser
# params.  Any field-set change must be mirrored in both files.

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache

from wizbuilder.noderender import _wide_int
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


def add_kb(bundle: InputBundle, params: dict, minter) -> None:
    """Append a knowledge base in wiz-builder's BizKnowledgeInfo shape (knowledge.py).

    params:
        name        — kdTitle (required)
        intents     — list of intent names; each must exist in SpeechIntent
        answers     — list of answer text strings (one kdInfo item per answer)
        multi_round — optional component name; resolved to componentUuid for
                      the delegating answerType:2 item appended after answers

    Shape-of-record: wizbuilder/knowledge.py::apply_knowledge_bases.
    Field set duplicated here because knowledge.py expects a Manifest object;
    any field-set change must be mirrored in both files.
    """
    name: str = params["name"]
    intent_names: list[str] = list(params.get("intents") or [])
    answers: list[str] = list(params.get("answers") or [])
    multi_round: str | None = params.get("multi_round")

    # --- decode BizKnowledgeInfo ---
    bk_raw = bundle.data.get("BizKnowledgeInfo", "[]")
    bk_list: list[dict] = json.loads(bk_raw) if isinstance(bk_raw, str) else list(bk_raw)
    if not bk_list:
        raise ValueError(
            "add-kb: BizKnowledgeInfo is empty; baseline must carry default entries "
            "to clone config constants from"
        )

    # Dedup guard: raise loudly rather than silently creating a duplicate
    if any(kb.get("kdTitle") == name for kb in bk_list):
        raise ValueError(f"add-kb: knowledge base {name!r} already exists")

    base_kb = bk_list[0]
    speech_id: int = base_kb["speechId"]
    create_id: int = base_kb["createId"]
    create_time: int = base_kb["createTime"]
    modify_id: int = base_kb["modifyId"]
    modify_time: int = base_kb["modifyTime"]
    exclusive_key_words: str = base_kb.get("exclusiveKeyWords", "[]")
    branch: str = base_kb.get("branch", "dev")

    # --- resolve intents from SpeechIntent ---
    si_raw = bundle.data.get("SpeechIntent", "[]")
    si_list: list[dict] = json.loads(si_raw) if isinstance(si_raw, str) else list(si_raw)
    intent_id_by_name: dict[str, int] = {
        i["intentName"]: i["intentId"] for i in si_list
    }
    resolved_intents: list[dict] = []
    for intent_name in intent_names:
        if intent_name not in intent_id_by_name:
            raise ValueError(
                f"add-kb: KB {name!r} references intent {intent_name!r} which is not "
                f"in the export's SpeechIntent list; add it first with add-intent"
            )
        resolved_intents.append({
            "intentName": intent_name,
            "intentId": intent_id_by_name[intent_name],
        })

    # --- resolve multi_round component name → componentUuid ---
    multi_round_uuid: str | None = None
    if multi_round is not None:
        bsc_raw = bundle.data.get("BizSpeechComponent", "[]")
        bsc_list: list[dict] = json.loads(bsc_raw) if isinstance(bsc_raw, str) else list(bsc_raw)
        comp_uuid_by_name: dict[str, str] = {
            c.get("name", ""): c.get("componentUuid", "") for c in bsc_list
        }
        if multi_round not in comp_uuid_by_name or not comp_uuid_by_name[multi_round]:
            raise ValueError(
                f"add-kb: KB {name!r} multi_round target {multi_round!r} not found "
                f"in BizSpeechComponent; ensure the component exists"
            )
        multi_round_uuid = comp_uuid_by_name[multi_round]

    # --- build kdInfo items (one per answer + optional delegate item) ---
    # Item ids use _wide_int seeded from a deterministic string; mirrors knowledge.py.
    # minter.manifest_hash is available on all IdMinter instances; on a modifier minter
    # it is set from the input export hash.
    manifest_hash: str = getattr(minter, "manifest_hash", "modifier")
    kd_info_items: list[dict] = []
    for ai, answer_text in enumerate(answers):
        item_id = str(_wide_int(f"{manifest_hash}:kdinfo:{name}:{ai}"))
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

    if multi_round_uuid is not None:
        delegate_item_id = str(minter.uuid(f"kdinfo-delegate:{name}"))
        kd_info_items.append({
            "answerType": 2,
            "editorValue": {
                "xml": '<speak xmlns:wiz="http://www.wiz.ai/develop/xml/tts"></speak>',
                "html": "<p></p>",
                "text": "",
            },
            "id": delegate_item_id,
            "multipleAppointId": multi_round_uuid,
        })

    # Mint a fresh knowledgeId for this KB.
    knowledge_id: int = minter.int_id(f"add-kb:{name}")

    bk_entry: dict = {
        "allowInterrupt": 1,
        "answerType": 1,
        "branch": branch,
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
        "kdTitle": name,
        "kdType": 0,
        "knowledgeId": knowledge_id,
        "modifyId": modify_id,
        "modifyTime": modify_time,
        "nodeResponseDurationSwitch": base_kb.get("nodeResponseDurationSwitch", 0),
        "noticeSendType": 0,
        "recordNum": 0,
        "repeatScriptType": 1,
        "soundexMatch": 0,
        "speakType": 1,
        "speechId": speech_id,
        "tagList": "[]",
        "threshold": "",
        "valueAssignment": "[]",
        "wordNum": 0,
    }
    bk_list.append(bk_entry)

    # --- decode SentenceCutKnowledge; emit one SCK row per answerType:1 answer ---
    sck_raw = bundle.data.get("SentenceCutKnowledge", "[]")
    sck_list: list[dict] = json.loads(sck_raw) if isinstance(sck_raw, str) else list(sck_raw)
    for ai, answer_text in enumerate(answers):
        item_id = str(_wide_int(f"{manifest_hash}:kdinfo:{name}:{ai}"))
        krec_cut_id: int = minter.int_id(f"sck-knowledgeRecCutId:{name}:{ai}")
        speech_rec_cut_id: str = str(minter.uuid(f"sck-speechRecCutId:{name}:{ai}"))
        sck_list.append({
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
        })

    bundle.data["BizKnowledgeInfo"] = codec.encode(bk_list)
    bundle.data["SentenceCutKnowledge"] = codec.encode(sck_list)
