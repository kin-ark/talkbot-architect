"""Loader for the WIZ facts substrate.

facts/*.yaml is the source of truth. Every fact is validated against
facts/_meta.schema.yaml at load. The loader fails loud (raises FactsError)
on a malformed, uncited, unquoted, or duplicate-id fact so bad data never
reaches a consuming agent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

_FACTS_DIR = Path(__file__).resolve().parents[2] / "facts"
_META_SCHEMA_PATH = _FACTS_DIR / "_meta.schema.yaml"


class FactsError(Exception):
    """Raised when a facts file is malformed or violates the meta-schema."""


class Facts:
    """Immutable lookup over all loaded facts, keyed by dotted id."""

    def __init__(self, by_id: dict[str, Any], sources: dict[str, Any]) -> None:
        self._by_id = by_id
        self._sources = sources

    def get(self, fact_id: str) -> Any:
        """Return a fact's value. Raises KeyError if the id is unknown."""
        if fact_id not in self._by_id:
            raise KeyError(f"unknown fact id: {fact_id!r}")
        return self._by_id[fact_id]["value"]

    def has(self, fact_id: str) -> bool:
        return fact_id in self._by_id

    def cite(self, fact_id: str) -> dict[str, Any]:
        """Return the citation dict for a fact (for audit / messages)."""
        if fact_id not in self._by_id:
            raise KeyError(f"unknown fact id: {fact_id!r}")
        return self._by_id[fact_id]["cite"]


def load_facts(facts_dir: Path | None = None) -> Facts:
    facts_dir = facts_dir or _FACTS_DIR
    try:
        schema = yaml.safe_load(_META_SCHEMA_PATH.read_text(encoding="utf-8"))
    except OSError as e:
        raise FactsError(f"cannot read meta-schema at {_META_SCHEMA_PATH}: {e}") from e
    validator = Draft7Validator(schema)

    by_id: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    for path in sorted(facts_dir.glob("*.yaml")):
        if path.name == "_meta.schema.yaml":
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            raise FactsError(f"{path.name}: cannot read/parse: {e}") from e
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            first = errors[0]
            loc = "/".join(str(p) for p in first.absolute_path) or "<root>"
            raise FactsError(f"{path.name}: meta-schema violation at {loc}: {first.message}")
        sources.update(data.get("source_manuals", {}))
        for fact in data["facts"]:
            fid = fact["id"]
            if fid in by_id:
                raise FactsError(f"{path.name}: duplicate fact id {fid!r}")
            by_id[fid] = fact
    return Facts(by_id, sources)
