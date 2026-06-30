import pytest

import persistence
from registry import Registry


# Override the autouse _isolate fixture from conftest so this file is
# self-contained and does not depend on the legacy CONFIG singleton.
@pytest.fixture(autouse=True)
def _isolate():
    yield


def test_lazy_one_store_per_client(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    reg = Registry()
    a1 = reg.store("alice")
    a2 = reg.store("alice")
    b = reg.store("bob")
    assert a1 is a2            # same client → same store
    assert a1 is not b         # different clients → different stores
    assert a1.owner == "alice" and b.owner == "bob"


def test_reset_clears(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    reg = Registry()
    first = reg.store("alice")
    reg.reset()
    assert reg.store("alice") is not first
