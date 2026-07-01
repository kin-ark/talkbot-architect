from wizcheck.flowmodel import KBView, _kb_to_dict, _build_kbs


def test_kbview_new_fields_default():
    kb = KBView(knowledge_id=1, title="T", kd_type=0, intents=[])
    assert kb.intent_names == []
    assert kb.answers == []
    assert kb.trigger_type == "intent"
    assert kb.is_user_created is False
    assert kb.multi_round_target is None


def test_kb_to_dict_emits_new_keys():
    kb = KBView(
        knowledge_id=7, title="Pay", kd_type=1, intents=[5],
        intent_names=["WantPay"], answers=[{"text": "Hi", "after": "wait"}],
        trigger_type="intent", is_user_created=True, multi_round_target="MR Comp",
    )
    d = _kb_to_dict(kb)
    assert d["intent_names"] == ["WantPay"]
    assert d["answers"] == [{"text": "Hi", "after": "wait"}]
    assert d["trigger_type"] == "intent"
    assert d["is_user_created"] is True
    assert d["multi_round_target"] == "MR Comp"


def _kb_fixture():
    return {
        "SpeechIntent": [
            {"intentId": 5, "intentName": "WantPay"},
            {"intentId": 6, "intentName": "Refuse"},
        ],
        "BizKnowledgeInfo": [
            {
                "knowledgeId": 100, "kdTitle": "Payment KB", "kdType": 1,
                "isInit": 0, "conditions": "null",
                "intents": [{"intentId": 5}, {"intentId": 6}],
                "kdInfo": [
                    {"answerType": 1, "answer": "Please pay now.", "afterSentence": 0},
                    {"answerType": 1, "answer": "Goodbye.", "afterSentence": 1},
                ],
            },
            {
                "knowledgeId": 200, "kdTitle": "System KB", "kdType": 0,
                "isInit": 1, "conditions": [{"type": 0}],
                "intents": [], "kdInfo": [],
            },
        ],
    }


def test_build_kbs_intent_names_resolved():
    kbs = _build_kbs(_kb_fixture())
    pay = next(k for k in kbs if k.knowledge_id == 100)
    assert pay.intent_names == ["WantPay", "Refuse"]


def test_build_kbs_answers_with_after():
    kbs = _build_kbs(_kb_fixture())
    pay = next(k for k in kbs if k.knowledge_id == 100)
    assert pay.answers == [
        {"text": "Please pay now.", "after": "wait"},
        {"text": "Goodbye.", "after": "hangup"},
    ]


def test_build_kbs_trigger_type_and_user_flag():
    kbs = _build_kbs(_kb_fixture())
    pay = next(k for k in kbs if k.knowledge_id == 100)
    sysk = next(k for k in kbs if k.knowledge_id == 200)
    assert pay.trigger_type == "intent" and pay.is_user_created is True
    assert sysk.trigger_type == "system" and sysk.is_user_created is False


def test_build_kbs_missing_intent_name_falls_out():
    data = _kb_fixture()
    data["SpeechIntent"] = [{"intentId": 5, "intentName": "WantPay"}]  # 6 has no name
    kbs = _build_kbs(data)
    pay = next(k for k in kbs if k.knowledge_id == 100)
    assert pay.intent_names == ["WantPay"]  # id 6 dropped (no name); raw intents still [5, 6]
    assert pay.intents == [5, 6]
