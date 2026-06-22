from session import Session


def test_apply_then_undo_redo():
    s = Session()
    s.load({"v": 0})
    s.apply({"v": 1})
    assert s.current() == {"v": 1} and s.can_undo()
    assert s.undo() and s.current() == {"v": 0}
    assert s.redo() and s.current() == {"v": 1}


def test_undo_at_base_returns_false():
    s = Session()
    s.load({"v": 0})
    assert s.undo() is False
