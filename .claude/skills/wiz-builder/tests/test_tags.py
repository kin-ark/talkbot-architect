import textwrap

import pytest

from wizbuilder.manifest import ManifestError, load_manifest


def _write(tmp_path, body):
    p = tmp_path / "m.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def test_manifest_parses_tags_and_node_assignment(tmp_path):
    m = load_manifest(_write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    enterprise_id: 999
    tags:
      - name: Debt Result
        is_mutex: true
        values: [Refuse Payment, Willing to Repay]
      - name: Payment Method
        type: 3
        values: [""]
    canvases:
      - name: Main
        nodes:
          - id: greet
            type: talk
            prompt: Hi
            tags:
              - {category: Debt Result, values: [Willing to Repay]}
          - id: bye
            type: exit
            prompt: Bye
        edges:
          - {from: greet, branch: Unclassified, to: bye}
    """))
    assert m.enterprise_id == 999
    assert len(m.tags) == 2
    debt = m.tags[0]
    assert debt.name == "Debt Result"
    assert debt.is_mutex is True
    assert debt.type == 0
    assert debt.values == ("Refuse Payment", "Willing to Repay")
    assert m.tags[1].type == 3
    greet = m.canvases[0].nodes[0]
    assert len(greet.tags) == 1
    assert greet.tags[0].category == "Debt Result"
    assert greet.tags[0].values == ("Willing to Repay",)
    assert m.canvases[0].nodes[1].tags == ()


def test_manifest_rejects_duplicate_category(tmp_path):
    with pytest.raises(ManifestError, match="duplicate tag category"):
        load_manifest(_write(tmp_path, """
        name: Tag Bot
        branch: dev
        language: IDN
        tags:
          - {name: Dup, values: [a]}
          - {name: Dup, values: [b]}
        canvases:
          - name: Main
            nodes: [{id: n, type: talk, prompt: x}]
        """))


def test_manifest_rejects_duplicate_value_in_category(tmp_path):
    with pytest.raises(ManifestError, match="duplicate tag value"):
        load_manifest(_write(tmp_path, """
        name: Tag Bot
        branch: dev
        language: IDN
        tags:
          - {name: C, values: [a, a]}
        canvases:
          - name: Main
            nodes: [{id: n, type: talk, prompt: x}]
        """))


import json

from wizbuilder.ids import IdMinter
from wizbuilder.tags import apply_tags, build_tag_vocabulary
from wizbuilder.compile import CompileError


def _manifest_with_tags(tmp_path):
    return load_manifest(_write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    enterprise_id: 999
    tags:
      - name: Debt Result
        is_mutex: true
        values: [Refuse Payment, Willing to Repay]
      - name: Unused
        values: [x]
    canvases:
      - name: Main
        nodes:
          - id: greet
            type: talk
            prompt: Hi
            tags:
              - category: Debt Result
                values: [Willing to Repay]
          - id: bye
            type: exit
            prompt: Bye
        edges:
          - {from: greet, branch: Unclassified, to: bye}
    """))


def test_build_vocabulary_mints_ids_and_entid(tmp_path):
    m = _manifest_with_tags(tmp_path)
    minter = IdMinter(manifest_hash="h")
    vocab = build_tag_vocabulary(m, minter)
    assert vocab.ent_id == 999
    assert set(vocab.categories) == {"Debt Result", "Unused"}
    debt = vocab.categories["Debt Result"]
    assert isinstance(debt.id, int)
    assert set(debt.values) == {"Refuse Payment", "Willing to Repay"}
    # deterministic
    assert build_tag_vocabulary(m, IdMinter(manifest_hash="h")).categories["Debt Result"].id == debt.id


def test_build_vocabulary_minted_entid_when_absent(tmp_path):
    m = load_manifest(_write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    tags:
      - name: C
        values: [a]
    canvases:
      - name: Main
        nodes:
          - id: n
            type: talk
            prompt: x
    """))
    vocab = build_tag_vocabulary(m, IdMinter(manifest_hash="h"))
    assert isinstance(vocab.ent_id, int) and vocab.ent_id != 0


def test_build_vocabulary_rejects_unknown_category(tmp_path):
    m = load_manifest(_write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    tags:
      - name: C
        values: [a]
    canvases:
      - name: Main
        nodes:
          - id: n
            type: talk
            prompt: x
            tags:
              - category: Nope
                values: [a]
    """))
    with pytest.raises(CompileError, match="unknown tag category"):
        build_tag_vocabulary(m, IdMinter(manifest_hash="h"))


def test_build_vocabulary_rejects_unknown_value(tmp_path):
    m = load_manifest(_write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    tags:
      - name: C
        values: [a]
    canvases:
      - name: Main
        nodes:
          - id: n
            type: talk
            prompt: x
            tags:
              - category: C
                values: [zzz]
    """))
    with pytest.raises(CompileError, match="unknown tag value"):
        build_tag_vocabulary(m, IdMinter(manifest_hash="h"))


def test_apply_tags_emits_speechtag_and_kbtag(tmp_path):
    m = _manifest_with_tags(tmp_path)
    minter = IdMinter(manifest_hash="h")
    vocab = build_tag_vocabulary(m, minter)
    template = {"SpeechTag": "[]", "kbTag": []}
    out = apply_tags(template, m, vocab, minter)
    st = json.loads(out["SpeechTag"])
    assert {c["name"] for c in st} == {"Debt Result", "Unused"}
    debt = next(c for c in st if c["name"] == "Debt Result")
    assert debt["isMutex"] == 1
    assert debt["entId"] == 999
    assert {p["value"] for p in debt["bizTagPropertyDTOS"]} == {"Refuse Payment", "Willing to Repay"}
    assert all(isinstance(p["id"], int) for p in debt["bizTagPropertyDTOS"])
    # kbTag = only categories a node assigned (Debt Result), not Unused
    assert out["kbTag"] == [vocab.categories["Debt Result"].id]


def test_apply_tags_noop_without_tags(tmp_path):
    m = load_manifest(_write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    canvases:
      - name: Main
        nodes:
          - id: n
            type: talk
            prompt: x
    """))
    template = {"SpeechTag": "[]", "kbTag": []}
    out = apply_tags(template, m, build_tag_vocabulary(m, IdMinter(manifest_hash="h")), IdMinter(manifest_hash="h"))
    assert out["SpeechTag"] == "[]"
    assert out["kbTag"] == []


def test_component_mode_rejects_tags(tmp_path):
    from wizbuilder.compile import compile_manifest
    mp = _write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    tags:
      - name: C
        values: [a]
    canvases:
      - name: Main
        nodes:
          - id: n
            type: talk
            prompt: x
    """)
    with pytest.raises(CompileError, match="component mode"):
        compile_manifest(mp, tmp_path / "out.json", emit="component")


def test_component_mode_rejects_node_tags(tmp_path):
    from wizbuilder.compile import compile_manifest
    mp = _write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    tags:
      - name: C
        values: [a]
    canvases:
      - name: Main
        nodes:
          - id: n
            type: talk
            prompt: x
            tags:
              - category: C
                values: [a]
    """)
    with pytest.raises(CompileError, match="component mode"):
        compile_manifest(mp, tmp_path / "out.json", emit="component")


def test_end_to_end_node_tag_list_and_checker_clean(tmp_path):
    from wizbuilder.compile import compile_manifest

    mp = _write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    enterprise_id: 999
    tags:
      - name: Debt Result
        is_mutex: true
        values: [Refuse Payment, Willing to Repay]
    canvases:
      - name: Main
        nodes:
          - id: greet
            type: talk
            prompt: Hi
            tags:
              - category: Debt Result
                values: [Willing to Repay]
          - id: bye
            type: exit
            prompt: Bye
        edges:
          - {from: greet, branch: Unclassified, to: bye}
    """)
    out = tmp_path / "out.json"
    result = compile_manifest(mp, out, emit="full")
    assert result.finding_codes.get("WIZ401", 0) == 0
    assert result.finding_codes.get("WIZ402", 0) == 0

    data = json.loads(out.read_text(encoding="utf-8"))
    comps = json.loads(data["BizSpeechComponent"])
    details = json.loads(comps[0]["details"])
    # find the greet talk node (type 1) with a tag_list
    tagged = [n for n in details.values() if (n.get("data") or {}).get("tag_list")]
    assert len(tagged) == 1
    tl = tagged[0]["data"]["tag_list"]
    assert len(tl) == 1
    cat = tl[0]
    assert cat["name"] == "Debt Result"
    assert isinstance(cat["id"], str)          # denormalized: string ids
    assert isinstance(cat["entId"], str)
    rows = cat["bizTagPropertyDTOS"]
    assert len(rows) == 1                        # only the SELECTED value
    assert rows[0]["value"] == "Willing to Repay"
    assert rows[0]["active"] is True
    assert isinstance(rows[0]["id"], str) and isinstance(rows[0]["tagId"], str)
    # exactly one node carries a non-empty tag_list (the greet node)
    with_tl = [n for n in details.values() if (n.get("data") or {}).get("tag_list")]
    assert len(with_tl) == 1


def test_no_tags_manifest_leaves_speechtag_empty(tmp_path):
    from wizbuilder.compile import compile_manifest
    mp = _write(tmp_path, """
    name: Tag Bot
    branch: dev
    language: IDN
    canvases:
      - name: Main
        nodes:
          - id: g
            type: talk
            prompt: Hi
          - id: b
            type: exit
            prompt: Bye
        edges:
          - {from: g, branch: Unclassified, to: b}
    """)
    out = tmp_path / "out.json"
    compile_manifest(mp, out, emit="full")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["SpeechTag"] == "[]"
    assert data["kbTag"] == []
    comps = json.loads(data["BizSpeechComponent"])
    details = json.loads(comps[0]["details"])
    # all nodes should have empty tag_lists (no assigned tags)
    assert all((n.get("data") or {}).get("tag_list") == [] for n in details.values())
