"""Shared test isolation: tmp persistence path, fresh registry + configs per test."""
import importlib
import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    import config_store
    config_store._CONFIGS.clear()

    try:
        persistence = importlib.import_module("persistence")
        monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path / ".sessions", raising=False)
        monkeypatch.setattr(persistence, "LEGACY_PATH", tmp_path / ".session" / "state.json", raising=False)
    except ModuleNotFoundError:
        pass

    try:
        import main
        main.REGISTRY.reset()
    except Exception:
        pass
    yield
