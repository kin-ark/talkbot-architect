"""Tests for GET /export/component endpoint."""
from __future__ import annotations

import io
import json
import pytest
import zipfile

from fastapi.testclient import TestClient

import main
from main import app

_client = TestClient(app)


def _minimal_bot_data():
    """Minimal bot data for testing."""
    return {
        "BizSpeechComponent": json.dumps([
            {
                "componentUuid": "comp-1",
                "name": "Main Flow",
                "category": 1,
                "details": "{}",
            },
            {
                "componentUuid": "comp-2",
                "name": "Multi Round",
                "category": 2,
                "details": "{}",
            },
        ]),
        "SpeechIntent": json.dumps([
            {
                "intentId": 1,
                "intentName": "Positive",
                "isInit": 1,
                "isDelete": 0,
                "keyWordInIntent": "[yes,yeah]",
                "userResponseInIntent": "[]",
                "language": "IDN",
            },
            {
                "intentId": 2,
                "intentName": "System Intent",
                "isInit": 0,
                "isDelete": 0,
                "keyWordInIntent": "[beep]",
                "userResponseInIntent": "[]",
                "language": "IDN",
            },
        ]),
        "BizKnowledgeInfo": json.dumps([
            {
                "knowledgeId": 1,
                "kdTitle": "User KB",
                "isInit": 0,
                "isDelete": 0,
                "intents": json.dumps([{"intentId": 1, "intentName": "Positive"}]),
                "kdInfo": json.dumps([
                    {"answerType": 1, "answer": "Yes, we can help", "id": "a1"}
                ]),
            },
            {
                "knowledgeId": 2,
                "kdTitle": "System KB",
                "isInit": 1,
                "isDelete": 0,
                "intents": json.dumps([]),
                "kdInfo": json.dumps([
                    {"answerType": 1, "answer": "System response", "id": "s1"}
                ]),
            },
        ]),
        "SpeechVariable": "[]",
        "SentenceCutSpeech": "[]",
        "SentenceCutKnowledge": "[]",
        "kbTag": [],
    }


@pytest.fixture(autouse=True)
def _reset_session():
    """Set up a fresh session with test data."""
    _client.get("/health")
    tbid = _client.cookies.get("tbid")
    if tbid:
        s = main.REGISTRY.store(tbid).active()
        s._stack = []
        s._idx = -1
        s.pending = None
        s.transcript = []
        s.is_component = False
        s.load(_minimal_bot_data())
    yield
    main.app.dependency_overrides.clear()


def test_export_component_single_uuid_returns_json():
    """Exporting a single component by uuid should return a JSON file."""
    r = _client.get("/export/component?uuid=comp-1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    assert "component.json" in r.headers.get("content-disposition", "")
    body = json.loads(r.content)
    assert isinstance(body, dict)


def test_export_component_no_uuid_returns_zip():
    """Exporting whole dialog (no uuid) should return a ZIP bundle."""
    r = _client.get("/export/component")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "components.zip" in r.headers.get("content-disposition", "")

    # Verify ZIP contents
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    # Should have component JSON(s) and Excel files
    assert any(".component.json" in name for name in names), f"No .component.json in {names}"
    assert any("intents.xls" in name for name in names), f"No intents.xls in {names}"
    assert any("KB.xls" in name for name in names), f"No KB.xls in {names}"


def test_export_component_no_uuid_filters_system_intent(tmp_path):
    """The exported intent Excel should not include system intents (isInit==0)."""
    r = _client.get("/export/component")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))

    # Read the intents Excel file
    intent_files = [n for n in zf.namelist() if "intents.xls" in n]
    assert len(intent_files) == 1
    from wizmodifier.xlsx import read_rows
    # Write to tmp file and read back (read_rows expects a path)
    tmp_intent = tmp_path / "intents.xls"
    tmp_intent.write_bytes(zf.read(intent_files[0]))
    intent_rows = read_rows(tmp_intent)
    intent_names = {row[0] for row in intent_rows if row and row[0]}
    # Should have Positive (user intent), NOT System Intent (system intent)
    assert "Positive" in intent_names
    assert "System Intent" not in intent_names


def test_export_component_no_uuid_filters_system_kb(tmp_path):
    """The exported KB Excel should not include system KBs (isInit==1)."""
    r = _client.get("/export/component")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))

    # Read the KB Excel file
    kb_files = [n for n in zf.namelist() if "KB.xls" in n]
    assert len(kb_files) == 1
    from wizmodifier.xlsx import read_rows
    # Write to tmp file and read back (read_rows expects a path)
    tmp_kb = tmp_path / "kb.xls"
    tmp_kb.write_bytes(zf.read(kb_files[0]))
    kb_rows = read_rows(tmp_kb)
    kb_titles = {row[0] for row in kb_rows if row and row[0]}
    # Should have User KB, NOT System KB
    assert "User KB" in kb_titles
    assert "System KB" not in kb_titles


def test_export_component_no_uuid_includes_mr_components():
    """The exported ZIP should include (multi-round).component.json if MR components exist."""
    r = _client.get("/export/component")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    # Should have both main and multi-round components
    assert any(".component.json" in name and "multi-round" not in name for name in names)
    assert any("multi-round" in name for name in names)
