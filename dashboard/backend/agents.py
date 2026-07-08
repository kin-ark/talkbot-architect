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
from wizcheck.flowmodel import build_flow_model, flow_model_to_dict, unwrap  # noqa: E402

import yaml  # noqa: E402  (stdlib-adjacent; available in env)

from wizbuilder.compile import compile_manifest, CompileError   # noqa: E402
from wizbuilder.manifest import ManifestError                    # noqa: E402

from wizmodifier.io import InputBundle           # noqa: E402
from wizmodifier.apply import run_mods           # noqa: E402
from wizmodifier.registry import OP_REGISTRY     # noqa: E402
from wizmodifier import codec as _wm_codec       # noqa: E402
import diffing                                    # noqa: E402
import proposal_meta                              # noqa: E402


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


def _unpack(data: dict) -> dict:
    """Inverse of _ensure_packed: decode JSON-string top-level values to objects.
    summarize()/build_flow_model expect the unpacked export shape."""
    out: dict = {}
    for k, v in data.items():
        if isinstance(v, str):
            try:
                out[k] = _wm_codec.decode(v)
            except Exception:
                out[k] = v
        else:
            out[k] = v
    return out


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


def _node_tags(node: dict) -> list[dict]:
    """Flatten a node's data.tag_list → [{category, value}] (active values first)."""
    out: list[dict] = []
    try:
        tl = (node.get("data") or {}).get("tag_list") or []
        for entry in tl:
            if not isinstance(entry, dict):
                continue
            cat = entry.get("name") or ""
            props = entry.get("bizTagPropertyDTOS") or []
            active = [p for p in props if isinstance(p, dict) and p.get("active")]
            chosen = active or [p for p in props if isinstance(p, dict)]
            for p in chosen:
                v = p.get("value")
                if v:
                    out.append({"category": cat, "value": v})
    except Exception:  # noqa: BLE001
        pass
    return out


def list_tags(data: dict) -> list[dict]:
    """SpeechTag categories → [{category, category_id, values, node_count}]. Never raises."""
    cats: list[dict] = []
    try:
        for c in unwrap(data.get("SpeechTag")) or []:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id", ""))
            vals = [p.get("value") for p in (c.get("bizTagPropertyDTOS") or [])
                    if isinstance(p, dict) and p.get("value")]
            cats.append({"category": c.get("name", ""), "category_id": cid,
                         "values": vals, "node_count": 0})
    except Exception:  # noqa: BLE001
        return []
    # count nodes referencing each category id
    by_id = {c["category_id"]: c for c in cats}
    try:
        for comp in unwrap(data.get("BizSpeechComponent")) or []:
            det = comp.get("details") if isinstance(comp, dict) else None
            if not det or det in ("null", ""):
                continue
            tree = json.loads(det) if isinstance(det, str) else det
            for node in (tree.values() if isinstance(tree, dict) else []):
                for entry in ((node.get("data") or {}).get("tag_list") or []):
                    cid = str(entry.get("id", "")) if isinstance(entry, dict) else ""
                    if cid in by_id:
                        by_id[cid]["node_count"] += 1
    except Exception:  # noqa: BLE001
        pass
    return cats


def summarize(data: dict) -> dict:
    """Build a FlowModel from *data* and return it as a JSON-compatible dict.

    Uses the envelope-based FlowModel (build_flow_model), NOT the checker
    parser's FlowNodes (which read the UI nav tree where node type is None).
    """
    s = flow_model_to_dict(build_flow_model(data))
    try:
        s["tags"] = list_tags(data)
        for comp in s.get("components", []):
            for node in (comp.get("nodes") or {}).values():
                node["tags"] = _node_tags(node)
    except Exception:  # noqa: BLE001 — enrich is additive, never break summarize
        s.setdefault("tags", [])
    return s


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


def list_intents(data: dict) -> list[dict]:
    """Derive the intent list from raw SpeechIntent (dashboard-side; no engine).

    isInit == 1 marks a user-created intent (OPPOSITE of KB convention).
    needs_nlu mirrors checker WIZ305: a user intent with no keywords and no
    example user-responses. Never raises; skips malformed entries.
    """
    out: list[dict] = []
    for it in unwrap(data.get("SpeechIntent")) or []:
        if not isinstance(it, dict):
            continue
        name = it.get("intentName")
        if name is None:
            continue
        kw = [k for k in str(it.get("keyWordInIntent") or "").split(",") if k.strip()]
        ur = [u for u in str(it.get("userResponseInIntent") or "").split(";") if u.strip()]
        is_user = False
        try:
            is_user = int(it.get("isInit", 0) or 0) == 1
        except (ValueError, TypeError):
            is_user = False
        out.append({
            "id": it.get("intentId"),
            "name": str(name),
            "type": "user" if is_user else "system",
            "keyword_count": len(kw),
            "response_count": len(ur),
            "keywords": kw,
            "user_responses": ur,
            "needs_nlu": bool(is_user and not kw and not ur),
        })
    return out


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


def get_schema() -> dict:
    """Return the builder manifest schema, known node labels, and modifier op
    names so the LLM can author valid scaffold_bot params and ops."""
    schema_dir = skills_dir() / "wiz-builder" / "schema"
    manifest_schema: dict = {}
    node_labels: list[str] = []
    try:
        manifest_schema = yaml.safe_load(
            (schema_dir / "manifest.schema.yaml").read_text("utf-8")) or {}
    except Exception:
        manifest_schema = {}
    try:
        doc = yaml.safe_load((schema_dir / "known_node_labels.yaml").read_text("utf-8")) or {}
        node_labels = list(doc.get("labels", []))
    except Exception:
        node_labels = []
    return {
        "manifest_schema": manifest_schema,
        "node_labels": node_labels,
        "modifier_ops": sorted(OP_REGISTRY),
    }


def get_playbook(vertical: str) -> dict:
    """Corpus-derived blueprint for a bot vertical (e.g. 'debt_collection').
    Always includes general playbook as the maturity baseline."""
    import playbooks
    text = playbooks.get_playbook(vertical)
    general = playbooks.get_playbook("general")
    return {
        "found": text is not None,
        "vertical": vertical,
        "playbook": text,
        "general": general,             # always present — the maturity baseline
        "available": [p["id"] for p in playbooks.list_playbooks()],
    }


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
        before_summary = summarize(_unpack(packed))
        after_summary = summarize(_unpack(proposed))
        cs = proposal_meta.change_set(before_summary, after_summary)
        delta = diffing.checker_delta(packed, proposed)
        return {
            "ok": True,
            "proposed_data": proposed,
            "diff": diffing.unified_diff_of(packed, proposed),
            "checker_delta": delta,
            "proposed_summary": after_summary,
            "change_set": cs,
            "change_summary": proposal_meta.change_summary(cs, delta),
            "error": None,
        }
    except (ValueError, KeyError, yaml.YAMLError) as e:
        return {"ok": False, "error": str(e), "known_ops": sorted(OP_REGISTRY)}


_LANGUAGES = {"ENG", "IDN"}
_BRANCHES = {"dev", "prod"}


def propose_scaffold(params: dict) -> dict:
    """Validate typed bot params, assemble a wiz-builder manifest, dry-run build.

    params mirrors the manifest: name, language, branch, canvases[], plus
    optional custom_variables[] and custom_intents[]. Returns the propose_build
    shape augmented with diff/checker_delta for a brand-new document.
    """
    if not isinstance(params, dict):
        return {"ok": False, "proposed_data": None, "error": "params must be an object"}
    name = params.get("name")
    language = params.get("language")
    branch = params.get("branch")
    canvases = params.get("canvases")
    if not name or not isinstance(name, str):
        return {"ok": False, "proposed_data": None, "error": "name is required"}
    if language not in _LANGUAGES:
        return {"ok": False, "proposed_data": None,
                "error": f"language must be one of {sorted(_LANGUAGES)}"}
    if branch not in _BRANCHES:
        return {"ok": False, "proposed_data": None,
                "error": f"branch must be one of {sorted(_BRANCHES)}"}
    if not isinstance(canvases, list) or not canvases:
        return {"ok": False, "proposed_data": None, "error": "canvases must be a non-empty list"}

    manifest: dict = {"name": name, "branch": branch, "language": language}
    if params.get("custom_variables"):
        manifest["custom_variables"] = params["custom_variables"]
    if params.get("custom_intents"):
        manifest["custom_intents"] = params["custom_intents"]
    if params.get("knowledge_bases"):
        manifest["knowledge_bases"] = params["knowledge_bases"]
    manifest["canvases"] = canvases

    manifest_yaml = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)
    built = propose_build(manifest_yaml)
    if not built["ok"]:
        return {"ok": False, "proposed_data": None, "error": built["error"]}
    after_summary = summarize(built["proposed_data"])
    empty_summary = {"components": [], "knowledge_bases": []}
    cs = proposal_meta.change_set(empty_summary, after_summary)
    return {"ok": True, "proposed_data": built["proposed_data"],
            "diff": "(new dialogue scaffolded)", "checker_delta": None,
            "proposed_summary": after_summary, "change_set": cs,
            "change_summary": proposal_meta.change_summary(cs, None), "error": None}


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


def export_component_dto(data: dict, component_uuid: str | None = None) -> dict:
    """Emit a component-export envelope from a full dialog.

    component_uuid=None → the whole dialog (all components). Otherwise the named
    component plus any nested-child components (parentUuid chain). Never mutates
    `data`. Raises KeyError if the uuid is not present.
    """
    from wizcheck.component_adapter import full_to_component_export

    if component_uuid is None:
        return full_to_component_export(data)

    raw = data.get("BizSpeechComponent")
    comps = json.loads(raw) if isinstance(raw, str) else (raw or [])
    if not isinstance(comps, list):
        comps = []
    by_uuid = {c.get("componentUuid"): c for c in comps if isinstance(c, dict)}
    if component_uuid not in by_uuid:
        raise KeyError(component_uuid)

    # children map (parentUuid -> [componentUuid]) for transitive descendants
    children: dict[str, list[str]] = {}
    for c in comps:
        if isinstance(c, dict):
            children.setdefault(c.get("parentUuid"), []).append(c.get("componentUuid"))

    keep: set[str] = set()
    stack = [component_uuid]
    while stack:
        cu = stack.pop()
        if cu in keep:
            continue
        keep.add(cu)
        stack.extend(children.get(cu, []))

    subset = dict(data)  # shallow copy; replace only the components list
    subset["BizSpeechComponent"] = [by_uuid[u] for u in by_uuid if u in keep]
    return full_to_component_export(subset)


def component_export_warnings(data: dict) -> list[str]:
    """Warnings for sections that can't survive a component export (dropped)."""
    def _n(key):
        v = data.get(key)
        if isinstance(v, str):
            import json as _j
            try:
                v = _j.loads(v)
            except Exception:
                return 0
        return len(v) if isinstance(v, list) else 0

    out = []
    kb = _n("BizKnowledgeInfo")
    if kb:
        out.append(f"{kb} knowledge base{'s' if kb != 1 else ''} will not be included in the component export")
    hw = _n("BizNodeHotWords")
    if hw:
        out.append(f"{hw} hot-word row{'s' if hw != 1 else ''} will not be included in the component export")
    return out


def ensure_mature(data: dict) -> tuple[dict, dict]:
    """Deterministically lift a built export to the maturity bar (model-independent).

    Runs the modifier `complete-component` op on components that need it (idempotent:
    adds a missing Exit, Unclassified out-ports, wires unconnected branches).
    Skips multi-round components (category==2) and components that already have
    a terminal node. Never mutates `data`; best-effort (a component that can't
    be completed is left as-is). Returns (matured_data, report).
    """
    from wizcheck.report import DEPLOY_BLOCKER_CODES

    work = copy.deepcopy(data)
    comps = unwrap(work.get("BizSpeechComponent")) or []
    auto_fixed: list[str] = []
    ops: list[dict] = []

    # Filter to components that need completion: not multi-round and no terminal nodes
    for i, comp in enumerate(comps):
        # Skip multi-round components (category==2)
        if comp.get("category") == 2:
            continue
        # Check if component already has a terminal node (type 2/4/8/13 or exit_port)
        details_raw = comp.get("details")
        has_terminal = False
        if details_raw is not None:
            try:
                details = unwrap(details_raw)
                if isinstance(details, dict):
                    for node in details.values():
                        if isinstance(node, dict):
                            node_type = node.get("data", {}).get("type")
                            # Terminal types: 2 (exit), 4 (goto/exit_port), 8 (goto_kb), 13 (transfer)
                            if node_type in (2, 4, 8, 13):
                                has_terminal = True
                                break
            except Exception:  # noqa: BLE001 — malformed details; skip
                pass
        if not has_terminal:
            ops.append({"op": "complete-component", "component": i})

    if ops:
        try:
            r = propose_mods(work, yaml.safe_dump(ops))
            if r.get("ok"):
                work = r["proposed_data"]
                delta = r.get("checker_delta") or {}
                auto_fixed.append(f"auto-completed {len(ops)} component(s)")
                if delta:
                    auto_fixed.append(f"checker delta: {delta}")
        except Exception as e:  # noqa: BLE001 — best-effort; never break the proposal
            auto_fixed.append(f"auto-complete skipped: {e}")

    try:
        findings = validate(work)
    except Exception as e:  # noqa: BLE001 — validation failure; return original
        findings = []
        auto_fixed.append(f"validation failed: {e}")

    report = {
        "auto_fixed": auto_fixed,
        "residual_blockers": [f for f in findings if f.get("code") in DEPLOY_BLOCKER_CODES],
        "errors": [f for f in findings if f.get("severity") == "error"],
    }
    return work, report


_FEATURE_PALETTE = [
    "talk", "conditional", "assign", "nested", "goto", "goto_kb", "goto_mr",
    "talk_continue", "transfer", "exit", "knowledge_base", "multi_round",
    "hot_words", "disposition_tags", "trained_intents",
]
_NODE_TYPE_FEATURE = {
    1: "talk", 2: "exit", 4: "goto", 5: "talk_continue", 7: "conditional",
    8: "goto_kb", 9: "goto_mr", 10: "assign", 11: "nested", 13: "transfer",
}


def feature_coverage(data: dict) -> dict:
    """Deterministic report of which palette features a built export uses.

    Returns {"used": [...], "missing": [...]} partitioning _FEATURE_PALETTE.
    Advisory only (never forces features); pure; never raises.
    """
    used: set[str] = set()

    # node types + per-node disposition tags
    try:
        for comp in unwrap(data.get("BizSpeechComponent")) or []:
            det = comp.get("details") if isinstance(comp, dict) else None
            if not det or det in ("null", ""):
                continue
            tree = json.loads(det) if isinstance(det, str) else det
            for node in (tree.values() if isinstance(tree, dict) else []):
                d = node.get("data") or {}
                t = d.get("type")
                if t in _NODE_TYPE_FEATURE:
                    used.add(_NODE_TYPE_FEATURE[t])
                if d.get("tag_list"):
                    used.add("disposition_tags")
    except Exception:  # noqa: BLE001 — best-effort
        pass

    # KBs + multi-round
    try:
        kbs = unwrap(data.get("BizKnowledgeInfo")) or []
        if kbs:
            used.add("knowledge_base")
        for kb in kbs:
            kd = kb.get("kdInfo") if isinstance(kb, dict) else None
            kd = json.loads(kd) if isinstance(kd, str) else kd
            if isinstance(kd, list) and any(isinstance(i, dict) and i.get("answerType") == 2 for i in kd):
                used.add("multi_round")
                break
    except Exception:  # noqa: BLE001
        pass

    # hot-words
    try:
        if unwrap(data.get("BizNodeHotWords")):
            used.add("hot_words")
    except Exception:  # noqa: BLE001
        pass

    # disposition tags (top-level SpeechTag)
    try:
        if unwrap(data.get("SpeechTag")):
            used.add("disposition_tags")
    except Exception:  # noqa: BLE001
        pass

    # trained intents (user-created with keywords/responses)
    try:
        for it in unwrap(data.get("SpeechIntent")) or []:
            if not isinstance(it, dict):
                continue
            if str(it.get("isInit")) == "1" and (it.get("keyWordInIntent") or it.get("userResponseInIntent")):
                used.add("trained_intents")
                break
    except Exception:  # noqa: BLE001
        pass

    return {"used": [f for f in _FEATURE_PALETTE if f in used],
            "missing": [f for f in _FEATURE_PALETTE if f not in used]}
