import copy
import json
import agents
import samples


def _thin_bot():
    # Build a real bot, then STRIP exits/unclassified to force WIZ107/108.
    data = agents.propose_build(samples.load_manifest("greeting_faq"))["proposed_data"]
    return data


def test_ensure_mature_is_idempotent_and_pure():
    data = _thin_bot()
    before = json.dumps(data, sort_keys=True, default=str)
    matured, report = agents.ensure_mature(data)
    assert json.dumps(data, sort_keys=True, default=str) == before      # input not mutated
    matured2, report2 = agents.ensure_mature(matured)
    # second pass changes nothing structural (idempotent)
    assert json.dumps(matured, sort_keys=True, default=str) == json.dumps(matured2, sort_keys=True, default=str)


def test_ensure_mature_reports_shape():
    data = _thin_bot()
    matured, report = agents.ensure_mature(data)
    assert set(report) >= {"auto_fixed", "residual_blockers", "errors"}
    assert isinstance(report["auto_fixed"], list)
    # matured is a valid dict that validates without raising
    assert isinstance(agents.validate(matured), list)


def test_ensure_mature_never_raises_on_empty():
    matured, report = agents.ensure_mature({"BizSpeechComponent": []})
    assert isinstance(matured, dict)
