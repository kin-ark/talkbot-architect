"""Top-level compile pipeline: manifest → speech*.json (checker-validated)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from wizbuilder.canvases import apply_canvases
from wizbuilder.identity import apply_identity
from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.intents import apply_intents
from wizbuilder.manifest import load_manifest
from wizbuilder.variables import apply_variables

_SKILL_DIR = Path(__file__).resolve().parents[2]
_TEMPLATE_PATH = _SKILL_DIR / "templates" / "empty_dialogue.json"
_PROJECT_ROOT = _SKILL_DIR.parents[2]
_CHECKER_CLI = _PROJECT_ROOT / ".claude" / "skills" / "wiz-checker" / "scripts" / "check.py"


@dataclass
class CompileResult:
    output_path: Path
    checker_errors: int
    checker_warnings: int
    finding_codes: dict[str, int]


def compile_manifest(manifest_path: Path, output_path: Path) -> CompileResult:
    """Compile a manifest into a checker-clean WIZ.AI export.

    Steps:
      1. load_manifest (parse + validate)
      2. load template (Empty+Dialogue snapshot)
      3. apply_identity
      4. apply_variables
      5. apply_intents
      6. apply_canvases
      7. serialize to output_path
      8. shell out to wiz-checker; verify errors == 0
    """
    manifest = load_manifest(manifest_path)
    template = _load_template()
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)
    template = apply_canvases(template, manifest, minter)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    result = _run_checker(output_path)
    if result.checker_errors > 0:
        # The compiler has a bug — delete the partial output.
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"compiler bug: wiz-checker rejected the output with "
            f"{result.checker_errors} errors. Codes: {result.finding_codes}"
        )
    return result


def _load_template() -> dict:
    return json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))


def _run_checker(output_path: Path) -> CompileResult:
    proc = subprocess.run(
        [sys.executable, str(_CHECKER_CLI), str(output_path), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"wiz-checker exited {proc.returncode} unexpectedly. stderr:\n{proc.stderr}"
        )
    report = json.loads(proc.stdout)
    summary = report["summary"]
    codes: dict[str, int] = {}
    for f in report["findings"]:
        codes[f["code"]] = codes.get(f["code"], 0) + 1
    return CompileResult(
        output_path=output_path,
        checker_errors=summary["errors"],
        checker_warnings=summary["warnings"],
        finding_codes=codes,
    )
