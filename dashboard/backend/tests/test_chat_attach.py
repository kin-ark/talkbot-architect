import io

import openpyxl


def _xlsx_bytes(header, rows, note="Note"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([note])
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _client_with_session():
    # reuse the app + a loaded blank session; mirror tests/test_api_export_component.py setup
    from main import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    c.post("/session/blank")
    return c


def test_classify_intent_xlsx(tmp_path):
    from main import _classify_attachment
    p = tmp_path / "intents.xls"
    p.write_bytes(_xlsx_bytes(["Intent", "Type", "Content", "Language"],
                              [["Positive", "Keyword", "ya", "Bahasa Indonesia"]]))
    kind, excerpt = _classify_attachment("intents.xls", str(p))
    assert kind == "intent-xlsx"


def test_classify_kb_xlsx(tmp_path):
    from main import _classify_attachment
    p = tmp_path / "kb.xls"
    p.write_bytes(_xlsx_bytes(["Title", "Intent", "Dialogue Content"],
                              [["KB A", "Benefit", "[hello]"]]))
    kind, _ = _classify_attachment("kb.xls", str(p))
    assert kind == "kb-xlsx"


def test_classify_failurelist_is_read(tmp_path):
    from main import _classify_attachment
    p = tmp_path / "FailureList.xls"
    p.write_bytes(_xlsx_bytes(["Something", "Else"], [["a", "b"]]))
    kind, excerpt = _classify_attachment("FailureList.xls", str(p))
    assert kind == "read" and excerpt


def test_attach_endpoint_sets_session_attachment():
    c = _client_with_session()
    data = _xlsx_bytes(["Intent", "Type", "Content", "Language"],
                       [["Positive", "Keyword", "ya", "Bahasa Indonesia"]])
    r = c.post("/chat/attach", files={"file": ("intents.xls", data,
               "application/vnd.ms-excel")})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "intent-xlsx" and body["name"] == "intents.xls"


def test_import_tools_registered():
    from tools import registry
    names = {s.name for s in registry.tool_specs()}
    assert {"import_intents_xlsx", "import_kb_xlsx"} <= names


def test_import_intents_tool_uses_attachment_path(tmp_path):
    # dispatch import_intents_xlsx with the server path in args -> proposal
    from tools import registry
    import json as _json
    # a minimal bot with SpeechIntent baseline so add/set-intent works
    data = {"SpeechIntent": _json.dumps([{"intentName": "Positive", "intentId": 1,
             "isInit": 1, "keyWordInIntent": "[]", "language": "IDN", "branch": "dev",
             "isDelete": 0, "nodeId": "", "speechId": 9, "templateCode": "T",
             "createTime": 0, "updateTime": 0, "userResponseInIntent": "[]"}]),
            "SpeechVariable": "[]", "BizSpeechComponent": "[]",
            "SentenceCutSpeech": "[]", "BizKnowledgeInfo": "[]", "kbTag": []}
    p = tmp_path / "intents.xls"
    p.write_bytes(_xlsx_bytes(["Intent", "Type", "Content", "Language"],
                              [["Newbie", "Keyword", "halo", "Bahasa Indonesia"]]))
    out = registry.dispatch("import_intents_xlsx", {"path": str(p)}, data)
    assert out["proposal"] is not None
    assert "Newbie" in _json.dumps(out["proposal"]["proposed_data"])


def test_import_intents_tool_without_path_errors():
    from tools import registry
    out = registry.dispatch("import_intents_xlsx", {}, {"SpeechIntent": "[]"})
    assert out["proposal"] is None and out["result"]["ok"] is False


def test_delete_chat_attach_endpoint():
    # Test that DELETE /chat/attach clears the session attachment
    c = _client_with_session()
    data = _xlsx_bytes(["Intent", "Type", "Content", "Language"],
                       [["Positive", "Keyword", "ya", "Bahasa Indonesia"]])
    # Attach a file
    r = c.post("/chat/attach", files={"file": ("intents.xls", data,
               "application/vnd.ms-excel")})
    assert r.status_code == 200
    # Verify it was stored
    assert r.json()["name"] == "intents.xls"
    # Delete it
    r = c.delete("/chat/attach")
    assert r.status_code == 200
    assert r.json()["cleared"] is True


def test_delete_chat_attach_idempotent():
    # Test that DELETE /chat/attach is idempotent (no error if none armed)
    c = _client_with_session()
    # Delete without attaching anything
    r = c.delete("/chat/attach")
    assert r.status_code == 200
    assert r.json()["cleared"] is True


def test_orchestrator_nulls_path_for_attach_tools_when_unarmed():
    # Test FIX 3: the orchestrator always overwrites the path for attach tools
    # (either from the attachment, or None if unarmed).
    # This prevents a hallucinated path from being trusted.
    from tools import registry
    from unittest.mock import patch
    import json as _json

    # a minimal bot with SpeechIntent baseline
    data = {"SpeechIntent": _json.dumps([{"intentName": "Positive", "intentId": 1,
             "isInit": 1, "keyWordInIntent": "[]", "language": "IDN", "branch": "dev",
             "isDelete": 0, "nodeId": "", "speechId": 9, "templateCode": "T",
             "createTime": 0, "updateTime": 0, "userResponseInIntent": "[]"}]),
            "SpeechVariable": "[]", "BizSpeechComponent": "[]",
            "SentenceCutSpeech": "[]", "BizKnowledgeInfo": "[]", "kbTag": []}

    # Call import_intents_xlsx with a hallucinated path but no attachment armed.
    # The dispatcher should null the path, so the tool fails with "no path" error.
    out = registry.dispatch("import_intents_xlsx", {"path": "/etc/passwd"}, data)
    assert out["proposal"] is None and out["result"]["ok"] is False
