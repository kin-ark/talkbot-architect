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
