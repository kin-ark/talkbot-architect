import zipfile, json
from pathlib import Path
import pytest
from wizcheck.parser import parse_dict
from wizcheck.flowmodel import build_flow_model

CORPUS = Path(__file__).resolve().parents[4] / "talkbot" / "Debt Collection" / "1108+-+[Main]+Due.zip"


@pytest.mark.skipif(not CORPUS.exists(), reason="corpus not present (gitignored)")
def test_corpus_type9_no_longer_unknown():
    z = zipfile.ZipFile(CORPUS)
    sj = [n for n in z.namelist() if n.lower().endswith(".json")][0]
    fm = build_flow_model(json.loads(z.read(sj)))
    types = {n.node_type for c in fm.components for n in c.nodes.values()}
    assert "talk_goto" in types
    assert "unknown" not in types  # type 9 was the only unknown source
