"""Tests for wizbuilder.variables — apply_variables step."""

from __future__ import annotations

import json

from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.manifest import Canvas, CustomVariable, Manifest, Node
from wizbuilder.variables import apply_variables


def _manifest(custom_vars: tuple[CustomVariable, ...]) -> Manifest:
    raw = "name: X\nbranch: dev\nlanguage: IDN\n"
    return Manifest(
        name="X",
        branch="dev",
        language="IDN",
        custom_variables=custom_vars,
        custom_intents=(),
        canvases=(Canvas(name="c", nodes=(Node(id="r", label="Greeting", parent=None),)),),
        raw_text=raw,
    )


def test_apply_variables_no_customs_keeps_defaults(template_dict):
    m = _manifest(())
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_variables(template_dict, m, minter)
    vars_ = json.loads(template_dict["SpeechVariable"])
    assert len(vars_) == 9  # the 9 default platform variables
    assert all(v["variableSource"] == 1 for v in vars_)


def test_apply_variables_appends_custom_with_source_0(template_dict):
    m = _manifest((CustomVariable(name="CLIENT_NAME"), CustomVariable(name="DUE_AMOUNT")))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_variables(template_dict, m, minter)
    vars_ = json.loads(template_dict["SpeechVariable"])
    assert len(vars_) == 11  # 9 defaults + 2 customs
    customs = [v for v in vars_ if v["variableSource"] == 0]
    assert len(customs) == 2
    names = {v["name"] for v in customs}
    assert names == {"CLIENT_NAME", "DUE_AMOUNT"}


def test_apply_variables_assigns_deterministic_ids(template_dict, template_path):
    m = _manifest((CustomVariable(name="A"),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_variables(template_dict, m, minter)
    vars_ = json.loads(template_dict["SpeechVariable"])
    custom = next(v for v in vars_ if v["variableSource"] == 0)

    # Re-run with a fresh template + fresh minter from the same manifest_hash.
    tpl2 = json.loads(template_path.read_text(encoding="utf-8"))
    minter2 = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_variables(tpl2, m, minter2)
    vars2 = json.loads(tpl2["SpeechVariable"])
    custom2 = next(v for v in vars2 if v["variableSource"] == 0)
    assert custom["id"] == custom2["id"]


def test_apply_variables_sets_text_type_empty_string(template_dict):
    """Custom variables (user-authored) have textType empty string."""
    m = _manifest((CustomVariable(name="MY_VAR"),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_variables(template_dict, m, minter)
    vars_ = json.loads(template_dict["SpeechVariable"])
    custom = next(v for v in vars_ if v["name"] == "MY_VAR")
    assert custom["textType"] == ""


def test_apply_variables_sets_speech_id_consistent_with_defaults(template_dict):
    """Custom variables inherit the same speechId as the default ones (single talkbot)."""
    m = _manifest((CustomVariable(name="X"),))
    minter = IdMinter(manifest_hash=manifest_hash_of(m.raw_text))
    apply_variables(template_dict, m, minter)
    vars_ = json.loads(template_dict["SpeechVariable"])
    default_speech_id = vars_[0]["speechId"]
    custom = next(v for v in vars_ if v["name"] == "X")
    assert custom["speechId"] == default_speech_id
