from wizcheck.flowmodel import KBView, _kb_to_dict


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
