import persistence
from fastapi.testclient import TestClient
import main


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions")
    main.REGISTRY.reset()
    import config_store
    config_store._CONFIGS.clear()


def test_two_clients_are_isolated(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    # Two TestClients = two cookie jars = two workspaces.
    with TestClient(main.app) as alice, TestClient(main.app) as bob:
        a = alice.post("/sessions").json()           # alice builds a slot
        assert a["id"]
        # alice's cookie was minted + echoed
        assert "tbid" in alice.cookies
        # bob sees an empty workspace
        assert bob.get("/sessions").json()["sessions"] == []
        # bob cannot activate alice's session id
        assert bob.post(f"/sessions/{a['id']}/activate").status_code == 404
        # alice still sees her own
        assert {e["id"] for e in alice.get("/sessions").json()["sessions"]} == {a["id"]}


def test_config_is_per_client(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    # Assert on env-derived config below — drop any ambient fallback so the test
    # is deterministic on a machine with a populated .env (LLM_MODEL/LLM_PROVIDER).
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    import models_catalog
    with TestClient(main.app) as alice, TestClient(main.app) as bob:
        alice.put("/config", json={"model_id": "deepseek-chat"})
        # Bob's model_id should be the default, not Alice's
        bob_config = bob.get("/config").json()
        alice_config = alice.get("/config").json()
        assert bob_config["model_id"] == models_catalog.default_entry_id()
        assert alice_config["model_id"] == "deepseek-chat"
        # They should have different models
        assert bob_config["model"] != alice_config["model"]
