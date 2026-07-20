"""Backend robustness: attachment temp cleanup + swap-vs-turn guard."""
import os
import tempfile
from fastapi.testclient import TestClient
import main
from session import Session


def _make_attachment():
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    return path


def test_load_unlinks_pending_attachment():
    s = Session()
    path = _make_attachment()
    s.attachment = {"path": path, "name": "x.xlsx", "kind": "kb-xlsx"}
    s.load({"BizSpeechComponent": "[]"})
    assert s.attachment is None
    assert not os.path.exists(path)      # temp file removed, not orphaned


def test_reset_unlinks_pending_attachment():
    s = Session()
    s.load({"BizSpeechComponent": "[]"})
    path = _make_attachment()
    s.attachment = {"path": path, "name": "x.xlsx", "kind": "kb-xlsx"}
    s.reset()
    assert s.attachment is None
    assert not os.path.exists(path)


def test_swap_refused_while_turn_holds_lock():
    """A session swap must not mutate the session while a chat turn holds the
    lock -> 409, not corruption."""
    with TestClient(main.app) as c:
        c.get("/health")
        tbid = c.cookies["tbid"]
        active = main.REGISTRY.store(tbid).active()
        active.load({"BizSpeechComponent": "[]"})
        active._lock.acquire()          # simulate an in-flight turn
        try:
            r = c.post("/session/blank")
            assert r.status_code == 409
        finally:
            active._lock.release()
        # lock free again -> swap works
        assert c.post("/session/blank").status_code == 200
