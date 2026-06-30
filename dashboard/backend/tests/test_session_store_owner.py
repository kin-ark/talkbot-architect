import pytest

import persistence
from session_store import SessionStore


# Override the autouse _isolate fixture from conftest so this file is
# self-contained and does not depend on the legacy CONFIG singleton.
@pytest.fixture(autouse=True)
def _isolate():
    yield


def test_stores_isolate_by_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    sa = SessionStore(owner="alice"); sa.new("A-bot"); sa.active().load({"BizSpeechComponent": []})
    sb = SessionStore(owner="bob")
    sb.boot()
    assert [e["name"] for e in sa.list()] == ["A-bot"]
    assert sb.list() == []                       # bob sees nothing of alice's
    assert sa.active().owner == "alice"


def test_boot_restores_own_active(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    s1 = SessionStore(owner="alice"); s1.new("A"); aid = s1.active().id
    s2 = SessionStore(owner="alice"); s2.boot()
    assert s2.active().id == aid
