"""Mod-manifest loader: parse YAML, validate against schema + the op registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

from wizmodifier.registry import OP_REGISTRY

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "mods.schema.yaml"


class ModManifestError(ValueError):
    """Raised when a mod-manifest is malformed or references an unknown op."""


@dataclass(frozen=True)
class ModManifest:
    input: str
    wav: str | None
    mods: list[dict]
    output_path: str
    output_format: str


def load_mods(path: Path) -> ModManifest:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ModManifestError("mod-manifest must be a YAML mapping")

    schema = yaml.safe_load(_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(raw), key=lambda e: list(e.path))
    if errors:
        msgs = "; ".join(e.message for e in errors)
        raise ModManifestError(f"mod-manifest schema violation: {msgs}")

    for entry in raw["mods"]:
        if entry["op"] not in OP_REGISTRY:
            raise ModManifestError(
                f"unknown op {entry['op']!r}; known ops: {', '.join(sorted(OP_REGISTRY))}"
            )

    return ModManifest(
        input=raw["input"],
        wav=raw.get("wav"),
        mods=raw["mods"],
        output_path=raw["output"]["path"],
        output_format=raw["output"]["format"],
    )
