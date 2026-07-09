import base64
import io


_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _client_with_session():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    c.post("/session/blank")
    return c


def test_image_media_type_detects_png():
    from main import _image_media_type
    assert _image_media_type("shot.png", _PNG) == "image/png"
    assert _image_media_type("note.txt", b"hello") is None


def test_attach_image_appends_to_images_not_attachment():
    c = _client_with_session()
    r = c.post("/chat/attach", files={"file": ("shot.png", _PNG, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "image" and body["count"] == 1


def test_attach_two_images_counts_two():
    c = _client_with_session()
    c.post("/chat/attach", files={"file": ("a.png", _PNG, "image/png")})
    r = c.post("/chat/attach", files={"file": ("b.png", _PNG, "image/png")})
    assert r.json()["count"] == 2


def test_fifth_image_rejected():
    c = _client_with_session()
    for i in range(4):
        c.post("/chat/attach", files={"file": (f"{i}.png", _PNG, "image/png")})
    r = c.post("/chat/attach", files={"file": ("x.png", _PNG, "image/png")})
    assert r.status_code in (400, 413)


def test_delete_one_image_by_index():
    c = _client_with_session()
    c.post("/chat/attach", files={"file": ("a.png", _PNG, "image/png")})
    c.post("/chat/attach", files={"file": ("b.png", _PNG, "image/png")})
    r = c.request("DELETE", "/chat/attach", params={"kind": "image", "index": 0})
    assert r.status_code == 200
    # one left
    r2 = c.post("/chat/attach", files={"file": ("c.png", _PNG, "image/png")})
    assert r2.json()["count"] == 2


def test_xlsx_attach_still_single_attachment():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Note"])
    ws.append(["Intent", "Type", "Content", "Language"])
    ws.append(["Positive", "Keyword", "ya", "Bahasa Indonesia"])
    buf = io.BytesIO()
    wb.save(buf)
    c = _client_with_session()
    r = c.post("/chat/attach", files={"file": ("intents.xls", buf.getvalue(),
               "application/vnd.ms-excel")})
    assert r.json()["kind"] == "intent-xlsx"     # unchanged single-attachment path
