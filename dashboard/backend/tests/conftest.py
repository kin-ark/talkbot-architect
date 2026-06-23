"""Shared test isolation: tmp persistence path, fresh CONFIG + SESSION per test."""
import importlib
import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    # Reset CONFIG overrides
    import config_store
    config_store.CONFIG.provider = None
    config_store.CONFIG.model = None
    config_store.CONFIG.base_url = None
    config_store.CONFIG.api_key = None

    # Point persistence at a throwaway path if the module exists yet
    try:
        persistence = importlib.import_module("persistence")
        monkeypatch.setattr(persistence, "STATE_PATH", tmp_path / "state.json", raising=False)
    except ModuleNotFoundError:
        pass

    # Reset the shared SESSION
    import main
    main.SESSION.__init__()
    yield
