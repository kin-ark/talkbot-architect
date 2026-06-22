"""Read-only agent wrappers (Task 7) + mutating dry-run wrapper (Task 9).

Exposes validate / summarize / read_node / get_facts as plain Python functions
that the LLM will call as tools in a later phase.

Import order is critical: add_skill_paths() must run before any wizcheck import
so that the checker's packages are on sys.path.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from paths import add_skill_paths, skills_dir

add_skill_paths()

from wizcheck.parser import parse_dict          # noqa: E402
from wizcheck.checks import run_all_checks      # noqa: E402
from flowmodel import build_flow_model, flow_model_to_dict, unwrap  # noqa: E402

import yaml  # noqa: E402  (stdlib-adjacent; available in env)

from wizbuilder.compile import compile_manifest, CompileError   # noqa: E402
from wizbuilder.manifest import ManifestError                    # noqa: E402

from wizmodifier.io import InputBundle           # noqa: E402
from wizmodifier.apply import run_mods           # noqa: E402
from wizmodifier.registry import OP_REGISTRY     # noqa: E402
from wizmodifier import codec as _wm_codec       # noqa: E402
import diffing                                    # noqa: E402


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_packed(data: dict) -> dict:
    """Return a version of *data* where every top-level list/dict value has been
    re-encoded as a compact JSON string (the WIZ modifier wire format).

    If a value is already a string it is left untouched.  This lets
    ``propose_mods`` accept both the raw export format (packed) and the
    pre-decoded variant (*.unpacked.json) used in tests/dev.
    """
    result: dict = {}
    for k, v in data.items():
        result[k] = _wm_codec.encode(v) if isinstance(v, (list, dict)) else v
    return result


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def validate(data: dict) -> list[dict]:
    """Run all checker rules against *data* and return findings as plain dicts.

    Each dict has keys: code, severity, entity, id, field, message.
    ``severity`` is always "error" or "warning".
    """
    wf = parse_dict(data)
    findings = run_all_checks(wf)
    return [
        {
            "code": f.code,
            "severity": f.severity.value,
            "entity": f.location.entity,
            "id": f.location.id,
            "field": f.location.field,
            "message": f.message,
        }
        for f in findings
    ]


def summarize(data: dict) -> dict:
    """Build a FlowModel from *data* and return it as a JSON-compatible dict.

    Uses the envelope-based FlowModel (build_flow_model), NOT the checker
    parser's FlowNodes (which read the UI nav tree where node type is None).
    """
    return flow_model_to_dict(build_flow_model(data))


def read_node(data: dict, uuid: str) -> dict | None:
    """Return the raw envelope for node *uuid*, or None if not found.

    Searches BizSpeechComponent[].details envelopes directly (envelope-based
    model, not the checker's FlowNode view).

    Return shape: {uuid, component, component_name, envelope}.
    """
    for comp in unwrap(data.get("BizSpeechComponent")):
        details_raw = comp.get("details")
        if details_raw is None:
            continue
        details = unwrap(details_raw)
        if not isinstance(details, dict):
            continue
        if uuid in details:
            return {
                "uuid": uuid,
                "component": comp.get("componentUuid"),
                "component_name": comp.get("name"),
                "envelope": details[uuid],
            }
    return None


def get_facts(query: str) -> list[dict]:
    """Keyword search over wiz-facts YAML files.

    Searches ``skills_dir() / "wiz-facts" / "facts" / "*.yaml"``.
    A fact matches if *query* (lowercased) appears anywhere in its
    ``id``, ``note``, or ``quote`` fields.
    """
    facts_dir = skills_dir() / "wiz-facts" / "facts"
    q = query.lower()
    matches: list[dict] = []

    for yaml_path in sorted(facts_dir.glob("*.yaml")):
        try:
            doc = yaml.safe_load(yaml_path.read_text("utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        for fact in doc.get("facts", []):
            if not isinstance(fact, dict):
                continue
            haystack = (
                f"{fact.get('id', '')} "
                f"{fact.get('note', '')} "
                f"{fact.get('quote', '')}"
            ).lower()
            if q in haystack:
                matches.append(fact)

    return matches


def propose_mods(data: dict, mods_yaml: str) -> dict:
    """Deep-copy *data*, apply *mods_yaml* ops as a dry-run, return diff + delta.

    Returns a dict with keys:
      ok             – True on success, False on any error
      proposed_data  – mutated deep copy (present only when ok=True)
      diff           – unified-diff string (present only when ok=True)
      checker_delta  – error/warning count delta (present only when ok=True)
      error          – error message string (present only when ok=False)
      known_ops      – sorted list of valid op names (present only when ok=False)
    """
    try:
        mods = yaml.safe_load(mods_yaml)
        if not isinstance(mods, list):
            return {"ok": False, "error": "mods must be a YAML list of {op: ...} entries"}
        packed = _ensure_packed(data)
        bundle = InputBundle(data=copy.deepcopy(packed), speech_name="speech.json")
        h = hashlib.sha256(mods_yaml.encode("utf-8")).hexdigest()
        run_mods(bundle, mods, manifest_hash=h)
        proposed = bundle.data
        return {
            "ok": True,
            "proposed_data": proposed,
            "diff": diffing.unified_diff_of(packed, proposed),
            "checker_delta": diffing.checker_delta(packed, proposed),
            "error": None,
        }
    except (ValueError, KeyError, yaml.YAMLError) as e:
        return {"ok": False, "error": str(e), "known_ops": sorted(OP_REGISTRY)}


def propose_build(manifest_yaml: str) -> dict:
    """Write *manifest_yaml* to a temp file, compile via wiz-builder, read JSON back.

    Returns a dict with keys:
      ok             – True on success, False on any error
      proposed_data  – the produced speech*.json as a dict (present only when ok=True)
      error          – error message string (present only when ok=False)
    """
    try:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.yaml"
            opath = Path(tmp) / "speech_build.json"
            mpath.write_text(manifest_yaml, encoding="utf-8")
            compile_manifest(mpath, opath)
            data = json.loads(opath.read_text(encoding="utf-8"))
        return {"ok": True, "proposed_data": data, "error": None}
    except (ManifestError, CompileError, ValueError) as e:
        return {"ok": False, "proposed_data": None, "error": str(e)}
