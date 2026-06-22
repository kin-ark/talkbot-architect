"""Read-only agent wrappers (Task 7).

Exposes validate / summarize / read_node / get_facts as plain Python functions
that the LLM will call as tools in a later phase.

Import order is critical: add_skill_paths() must run before any wizcheck import
so that the checker's packages are on sys.path.
"""
from __future__ import annotations

from paths import add_skill_paths, skills_dir

add_skill_paths()

from wizcheck.parser import parse_dict          # noqa: E402
from wizcheck.checks import run_all_checks      # noqa: E402
from flowmodel import build_flow_model, flow_model_to_dict, unwrap  # noqa: E402

import yaml  # noqa: E402  (stdlib-adjacent; available in env)


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
