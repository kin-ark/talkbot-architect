import json
import pathlib
import agents
import persistence
from session import Session
from wizcheck.component_adapter import is_component_export

FIX = pathlib.Path(__file__).parent / "fixtures" / "component_export_min.json"


def _raw():
    return json.loads(FIX.read_text(encoding="utf-8"))


def test_fixture_is_component_export():
    assert is_component_export(_raw())


def test_load_component_sets_flags():
    from wizcheck.component_adapter import component_export_to_full
    raw = _raw()
    full = component_export_to_full(raw)
    s = Session()
    s.load(full, is_component=True, component_base=raw)
    assert s.is_component is True
    assert s.component_base == raw
    # adapted doc validates + summarizes as a normal full doc
    assert isinstance(agents.validate(s.current()), list)
    assert agents.summarize(s.current())


def test_load_full_defaults_non_component():
    s = Session()
    s.load({"BizSpeechComponent": []})
    assert s.is_component is False and s.component_base is None


def test_persistence_roundtrips_component(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path)
    from wizcheck.component_adapter import component_export_to_full
    raw = _raw()
    s = Session()
    s.id = "csess"
    s.owner = "u1"
    s.load(component_export_to_full(raw), is_component=True, component_base=raw)
    persistence.save_session(s)
    s2 = Session()
    assert persistence.load_session(s2, sid="csess", owner="u1")
    assert s2.is_component is True and s2.component_base == raw


def test_persistence_old_snapshot_defaults_full(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "SESSIONS_DIR", tmp_path)
    s = Session()
    s.id = "old"
    s.owner = "u1"
    s.load({"BizSpeechComponent": []})
    persistence.save_session(s)
    # simulate an old snapshot: strip the new keys from the on-disk json
    p = tmp_path / "old.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d.pop("is_component", None)
    d.pop("component_base", None)
    p.write_text(json.dumps(d), encoding="utf-8")
    s2 = Session()
    assert persistence.load_session(s2, sid="old", owner="u1")
    assert s2.is_component is False and s2.component_base is None
