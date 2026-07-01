import json, sys
from pathlib import Path
_SK = Path(__file__).resolve().parents[2]
_REPO = _SK.parents[1]
sys.path.insert(0, str(_SK / "wiz-builder" / "scripts"))
from wizcheck.parser import parse_dict  # noqa: E402

_REAL = _REPO / "talkbot" / "[IN+USE]+Payment+Reminder+-+Non-IOH+Due_Overdue" / "speech12554783185497473808.json"


def test_global_hot_words_parsed():
    if not _REAL.exists():
        import pytest; pytest.skip("real export absent")
    wf = parse_dict(json.loads(_REAL.read_text(encoding="utf-8")))
    gw = wf.flow_model.global_hot_words
    assert any("indosat" in w or "tiktok" in w for w in gw) or len(gw) > 0  # global set present


def test_per_node_hot_words_attached():
    if not _REAL.exists():
        import pytest; pytest.skip("real export absent")
    wf = parse_dict(json.loads(_REAL.read_text(encoding="utf-8")))
    # the one populated node-scoped row (nodeId 7c476ef6-...) → that node carries hot_words
    nodes = {u: n for c in wf.flow_model.components for u, n in c.nodes.items()}
    n = nodes.get("7c476ef6-9032-4a99-80a2-7f28d5211422")
    if n is not None:
        assert "gojek" in n.hot_words
    # any node without a populated row → empty tuple
    assert all(isinstance(n.hot_words, tuple) for n in nodes.values())


def test_no_hotwords_table_is_safe():
    wf = parse_dict({"BizSpeechComponent": "[]", "SpeechIntent": "[]"})  # no BizNodeHotWords
    assert wf.flow_model.global_hot_words == ()
