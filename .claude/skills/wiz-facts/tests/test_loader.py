"""Tests for the wizfacts loader: discovery, meta-schema validation, fail-loud."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from wizfacts import Facts, FactsError, load_facts


def test_load_facts_returns_facts_object():
    facts = load_facts()
    assert isinstance(facts, Facts)


def test_get_returns_value_by_id():
    facts = load_facts()
    assert facts.get("lang.supported") == ["ZHO", "ENG", "IDN", "THA"]


def test_get_unknown_id_raises_keyerror():
    facts = load_facts()
    with pytest.raises(KeyError):
        facts.get("does.not.exist")


def test_uncited_fact_is_rejected(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(textwrap.dedent("""
        schema_version: 1
        source_manuals: {product: {title: x, version: y}}
        facts:
          - id: foo.bar
            value: 1
            confidence: documented
    """), encoding="utf-8")
    with pytest.raises(FactsError):
        load_facts(facts_dir=tmp_path)


def test_duplicate_id_across_files_is_rejected(tmp_path: Path):
    body = textwrap.dedent("""
        schema_version: 1
        source_manuals: {product: {title: x, version: y}}
        facts:
          - id: dup.id
            value: 1
            cite: {manual: product, pages: [1]}
            quote: "q"
            confidence: documented
    """)
    (tmp_path / "a.yaml").write_text(body, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(FactsError):
        load_facts(facts_dir=tmp_path)
