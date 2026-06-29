import speechname
from tools import registry


def _name_of(proposed: dict) -> str:
    return speechname.read_speech_name(proposed)


def test_build_proposal_sets_speech_name():
    manifest = (
        "name: My Debt Bot\n"
        "branch: dev\n"
        "language: IDN\n"
        "canvases:\n"
        "  - name: Main\n"
        "    nodes:\n"
        "      - id: n1\n"
        "        type: talk\n"
        "        prompt: Hello\n"
    )
    out = registry.dispatch("build", {"manifest_yaml": manifest}, {})
    assert out["proposal"] is not None
    assert _name_of(out["proposal"]["proposed_data"]) == "My Debt Bot"


def test_scaffold_proposal_sets_speech_name():
    args = {
        "name": "Survey Bot", "language": "IDN", "branch": "dev",
        "canvases": [{"name": "Main", "nodes": [{"id": "n1", "type": "talk", "prompt": "Hi"}]}],
    }
    out = registry.dispatch("scaffold_bot", args, {})
    assert out["proposal"] is not None
    assert _name_of(out["proposal"]["proposed_data"]) == "Survey Bot"
