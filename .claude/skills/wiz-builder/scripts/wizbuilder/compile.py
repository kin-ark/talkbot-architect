"""Top-level compile pipeline: manifest → speech*.json (checker-validated)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from wizbuilder.canvases import apply_canvases
from wizbuilder.hotwords import apply_hotwords
from wizbuilder.identity import apply_identity
from wizbuilder.ids import IdMinter, manifest_hash_of
from wizbuilder.intents import apply_intents
from wizbuilder.knowledge import apply_knowledge_bases
from wizbuilder.manifest import load_manifest
from wizbuilder.variables import apply_variables

_SKILL_DIR = Path(__file__).resolve().parents[2]
_TEMPLATE_PATH = _SKILL_DIR / "templates" / "empty_dialogue.json"
_PROJECT_ROOT = _SKILL_DIR.parents[2]
_CHECKER_CLI = _PROJECT_ROOT / ".claude" / "skills" / "wiz-checker" / "scripts" / "check.py"

_COMPONENT_FORBIDDEN_NODE_TYPES = frozenset({"goto_kb", "goto_mr", "talk_continue"})


class CompileError(RuntimeError):
    """Raised when wiz-checker reports errors > 0 against the compiler's output.

    This indicates a bug in the compiler itself (the produced speech*.json failed
    structural/logical validation). Distinct from plain RuntimeError, which is
    reserved for unexpected internal failures (e.g. checker crash, malformed JSON).
    """


def _validate_component_mode(manifest) -> None:
    """Reject bot-level features unsupported in a standalone component export."""
    if manifest.knowledge_bases:
        raise CompileError("knowledge_bases are not supported in component mode (--emit component)")
    if manifest.hot_words:
        raise CompileError("hot_words are not supported in component mode (--emit component)")
    for canvas in manifest.canvases:
        for node in canvas.nodes:
            if node.type in _COMPONENT_FORBIDDEN_NODE_TYPES:
                raise CompileError(
                    f"node {node.id!r} type {node.type!r} is not supported in component mode "
                    f"(--emit component) — needs bot-level KB/multi-round context"
                )


@dataclass
class CompileResult:
    output_path: Path
    checker_errors: int
    checker_warnings: int
    finding_codes: dict[str, int]


def compile_manifest(
    manifest_path: Path, output_path: Path, *, emit: str = "full"
) -> CompileResult:
    """Compile a manifest into a checker-clean WIZ.AI export.

    Steps:
      1. load_manifest (parse + validate)
      2. load template (Empty+Dialogue snapshot)
      3. apply_identity
      4. apply_variables
      5. apply_intents
      6. apply_canvases
      7. (optional) post-pass: transform to component-export DTO if emit=="component"
      8. serialize to output_path
      9. shell out to wiz-checker; verify errors == 0
    """
    manifest = load_manifest(manifest_path)

    if emit == "component":
        _validate_component_mode(manifest)
    template = _load_template()
    minter = IdMinter(manifest_hash=manifest_hash_of(manifest.raw_text))

    template = apply_identity(template, manifest, minter)
    template = apply_variables(template, manifest, minter)
    template = apply_intents(template, manifest, minter)

    # Pre-mint KB ids BEFORE apply_canvases so that talk nodes can include them
    # in allow_jump_knowledges.  ALL KBs (simple + multi-round) are pre-minted so
    # that multi-round KBs are also emitted in BizKnowledgeInfo and referenceable.
    kb_id_by_name: dict[str, int] = {
        kb.name: minter.int_id(f"kb:{kb.name}")
        for kb in manifest.knowledge_bases
    }

    template, canvas_uuid_by_name = apply_canvases(
        template, manifest, minter, kb_id_by_name=kb_id_by_name
    )
    template = apply_knowledge_bases(
        template, manifest, minter,
        kb_id_by_name=kb_id_by_name,
        canvas_uuid_by_name=canvas_uuid_by_name,
    )
    template = apply_hotwords(template, manifest, minter)

    if emit == "component":
        from wizcheck.component_adapter import full_to_component_export
        template = full_to_component_export(template, name=manifest.name)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(template, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    result = _run_checker(output_path)
    if result.checker_errors > 0:
        # The compiler has a bug — delete the partial output.
        output_path.unlink(missing_ok=True)
        raise CompileError(
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
    try:
        report = json.loads(proc.stdout)
        summary = report["summary"]
        findings = report["findings"]
        errors = summary["errors"]
        warnings = summary["warnings"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise RuntimeError(
            f"wiz-checker output is malformed ({type(e).__name__}: {e}). "
            f"stdout was:\n{proc.stdout[:500]}"
        ) from e
    codes: dict[str, int] = {}
    for f in findings:
        codes[f["code"]] = codes.get(f["code"], 0) + 1
    return CompileResult(
        output_path=output_path,
        checker_errors=errors,
        checker_warnings=warnings,
        finding_codes=codes,
    )
