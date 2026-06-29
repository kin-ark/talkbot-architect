import io
import json
import zipfile

import persistence
from fastapi.testclient import TestClient
from session import Session
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    monkeypatch.setattr(persistence, "ACTIVE_PATH", tmp_path / ".sessions" / "active")
    main.STORE._active = Session()
    main.SESSION = main.STORE.active()


def _named_doc(name="Debt Collector"):
    return {"BizSpeechComponent": [], "BizSpeechScene": json.dumps({"speechName": name})}


def _cd_filename(resp):
    return resp.headers["content-disposition"].split("filename=", 1)[1].strip().strip('"')


def test_export_zip_when_wavs_present(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    main.STORE.new()
    main.SESSION = main.STORE.active()
    main.STORE.active().load(_named_doc(), wavs={"abc_1_1.wav": b"RIFFfake"})
    with TestClient(main.app) as client:
        r = client.get("/export")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        assert _cd_filename(r) == "Debt_Collector.zip"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        assert z.testzip() is None
        names = z.namelist()
        assert "abc_1_1.wav" in names
        speech = [n for n in names if n.startswith("speech") and n.endswith(".json")]
        assert len(speech) == 1                      # exactly one speech*.json
        assert not any("/" in n for n in names)      # flat root
        parsed = json.loads(z.read(speech[0]).decode("utf-8"))
        assert "BizSpeechComponent" in parsed


def test_export_json_when_no_wavs(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    main.STORE.new()
    main.SESSION = main.STORE.active()
    main.STORE.active().load(_named_doc())
    with TestClient(main.app) as client:
        r = client.get("/export")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")
        assert _cd_filename(r) == "Debt_Collector.json"
        assert "BizSpeechComponent" in json.loads(r.content)


def test_zip_internal_entry_is_speech_even_when_speech_name_is_slug(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    main.STORE.new()
    main.SESSION = main.STORE.active()
    # the bot-name feature can set speech_name to a non-"speech" slug
    main.STORE.active().load(_named_doc(), speech_name="Debt_Collector.json",
                             wavs={"a_1_1.wav": b"RIFF"})
    with TestClient(main.app) as client:
        z = zipfile.ZipFile(io.BytesIO(client.get("/export").content))
        speech = [n for n in z.namelist() if n.startswith("speech") and n.endswith(".json")]
        assert len(speech) == 1                       # internal entry forced to speech*.json
        assert "Debt_Collector.json" not in z.namelist()


def test_export_requires_session(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)   # empty active session, no _stack
    with TestClient(main.app) as client:
        assert client.get("/export").status_code == 503
