"""Apply a sequence of mods to an InputBundle.

Reuses wiz-builder's IdMinter for any new-entity IDs. The wiz-builder scripts
dir is added to sys.path so `wizbuilder.ids` is importable as a sibling skill.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

_SKILL_DIR = Path(__file__).resolve().parents[2]
_WB_SCRIPTS = _SKILL_DIR.parent / "wiz-builder" / "scripts"
if str(_WB_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WB_SCRIPTS))

from wizbuilder.ids import IdMinter  # noqa: E402

from wizmodifier.io import InputBundle, write_output  # noqa: E402
from wizmodifier.registry import get_op  # noqa: E402

_PRESETS_DIR = _SKILL_DIR / "presets"

_RESULTS_TEMPLATE = """# Import Test Results

**Date:** YYYY-MM-DD
**WIZ.AI instance:** [URL]
**Tester:** [Name]

| Test | Result | Notes |
|------|--------|-------|
"""

_COMPONENT_FORBIDDEN_OPS = frozenset({
    "add-kb", "rename-kb", "set-kb-intents", "add-kb-answer", "edit-kb-answer",
    "remove-kb-answer", "set-kb-multiround", "delete-kb", "set-hotwords", "set-node-tags",
})
_COMPONENT_FORBIDDEN_NODE_TYPES = frozenset({"goto_kb", "goto_mr", "talk_continue"})


def _node_types_in_mod(entry: dict) -> list[str]:
    """Node type strings an append-node / add-component mod would emit."""
    op = entry.get("op")
    if op == "append-node":
        node = entry.get("node") or {}
        t = node.get("type")
        return [t] if t else []
    if op == "add-component":
        return [n.get("type") for n in (entry.get("nodes") or []) if n.get("type")]
    return []


def _guard_component_mods(mods: list[dict]) -> None:
    for entry in mods:
        op = entry.get("op")
        if op in _COMPONENT_FORBIDDEN_OPS:
            raise ValueError(f"component mode: op {op!r} unsupported")
        for t in _node_types_in_mod(entry):
            if t in _COMPONENT_FORBIDDEN_NODE_TYPES:
                raise ValueError(f"component mode: node type {t!r} unsupported")


def run_mods(bundle: InputBundle, mods: list[dict], manifest_hash: str) -> None:
    """Apply each mod in order, mutating the bundle in place.

    Raises ValueError (from an op) if a target is missing; the caller decides
    whether to write. No write happens here.
    """
    if bundle.is_component:
        _guard_component_mods(mods)
    minter = IdMinter(manifest_hash=manifest_hash)
    for i, entry in enumerate(mods):
        params = {k: v for k, v in entry.items() if k != "op"}
        op = get_op(entry["op"])
        try:
            op(bundle, params, minter)
        except (ValueError, KeyError) as e:
            raise ValueError(f"mod #{i + 1} ({entry['op']}): {e}") from e


def load_preset(name: str) -> list[dict]:
    path = _PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise ValueError(f"unknown preset {name!r} (looked in {_PRESETS_DIR})")
    return yaml.safe_load(path.read_text(encoding="utf-8"))["tests"]


def run_preset(
    base: InputBundle, name: str, out_dir: Path, manifest_hash: str
) -> list[Path]:
    """Run the preset cumulatively; write one file per test + results.md.

    Each test starts from the *previous* test's bundle. The bundle written for
    a test is a deep copy, so later tests' mutations don't bleed into earlier
    files.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tests = load_preset(name)
    written: list[Path] = []
    bundle = copy.deepcopy(base)
    rows = []
    for test in tests:
        run_mods(bundle, test["mods"], manifest_hash=manifest_hash)
        fmt = test["format"]
        ext = "json" if fmt == "json" else "zip"
        out_path = out_dir / f"{test['name']}.{ext}"
        write_output(copy.deepcopy(bundle), out_path, fmt=fmt)
        written.append(out_path)
        rows.append(f"| {test['name']} | ? | |")
    (out_dir / "results.md").write_text(
        _RESULTS_TEMPLATE + "\n".join(rows) + "\n", encoding="utf-8"
    )
    return written
