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
