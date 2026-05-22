#!/usr/bin/env python3
"""CLI entry: build a WIZ.AI talkbot from a manifest YAML.

Usage:
    python build.py --manifest <manifest.yaml> [--out <speech.json>] [--force]

Exit codes:
    0  Success (possibly with warnings)
    2  Manifest error (parse failure or schema violation)
    3  Output path conflict
    4  Internal compiler error
    5  Checker rejected the output (compiler bug)
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import traceback
from pathlib import Path

# Ensure stdout uses UTF-8 on Windows (em-dash characters can break cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

# Make the wizbuilder package importable when run directly.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from wizbuilder.compile import CompileError, compile_manifest  # noqa: E402
from wizbuilder.manifest import ManifestError, load_manifest  # noqa: E402


def _slugify(name: str) -> str:
    """Lowercase, replace whitespace with '+', strip everything not [A-Za-z0-9+_-]."""
    s = name.strip().lower()
    s = re.sub(r"\s+", "+", s)
    s = re.sub(r"[^A-Za-z0-9+_-]", "", s)
    return s or "talkbot"


def _resolve_output_path(manifest_path: Path, project_root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    manifest = load_manifest(manifest_path)
    slug = _slugify(manifest.name)
    speech_id = random.SystemRandom().randint(10**15, 10**16 - 1)
    return project_root / "talkbot" / slug / f"speech{speech_id}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a WIZ.AI talkbot from a manifest.")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest YAML")
    parser.add_argument(
        "--out", type=Path, default=None, help="Output speech*.json path (optional)"
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing output directory")
    args = parser.parse_args(argv)

    # Project root = three levels up from scripts/build.py (.claude/skills/wiz-builder/scripts).
    project_root = _SCRIPTS_DIR.parents[3]

    try:
        out_path = _resolve_output_path(args.manifest, project_root, args.out)
    except ManifestError as e:
        print(f"manifest error: {e}", file=sys.stderr)
        return 2

    out_dir = out_path.parent
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        print(
            f"output directory {out_dir} is not empty (use --force to overwrite)",
            file=sys.stderr,
        )
        return 3

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = compile_manifest(args.manifest, out_path)
    except ManifestError as e:
        print(f"manifest error: {e}", file=sys.stderr)
        return 2
    except CompileError as e:
        # Checker rejected the output — the compiler has a bug.
        print(f"compile failed: {e}", file=sys.stderr)
        return 5
    except Exception:
        traceback.print_exc()
        return 4

    # Compile succeeded — copy manifest alongside the output for self-contained builds.
    manifest_copy = out_dir / "manifest.yaml"
    if args.manifest.resolve() != manifest_copy.resolve():
        shutil.copy2(args.manifest, manifest_copy)

    print(json.dumps({
        "output": str(result.output_path),
        "errors": result.checker_errors,
        "warnings": result.checker_warnings,
        "codes": result.finding_codes,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
