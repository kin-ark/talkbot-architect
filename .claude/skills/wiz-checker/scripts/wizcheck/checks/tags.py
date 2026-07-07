"""WIZ4xx — tag (disposition) reference validation.

Reads raw IR (component.raw['details'] node tag_list + wf.raw['kbTag']) so it
runs even when flow_model is None. Tags are bot-scope: WIZ401/WIZ402 are in
BOT_SCOPE_CODES and suppressed for component-export inputs.
"""

from __future__ import annotations

import json
from typing import Any

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity


def _decode(raw: object) -> Any:
    if raw is None or raw in ("", "null", "0", 0):
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None
    return raw


def check_tags(wf: WizFile) -> list[Finding]:
    out: list[Finding] = []
    cat_by_id = {c.id: c for c in wf.tags}
    val_by_id = {v.id: v for c in wf.tags for v in c.values}

    # WIZ401: node data.tag_list references
    for comp in wf.components.values():
        details = _decode(comp.raw.get("details"))
        if not isinstance(details, dict):
            continue
        for node_uuid, node in details.items():
            if not isinstance(node, dict):
                continue
            tag_list = (node.get("data") or {}).get("tag_list") or []
            if not isinstance(tag_list, list):
                continue
            for cat in tag_list:
                if not isinstance(cat, dict):
                    continue
                cat_id = str(cat.get("id", ""))
                if cat_id not in cat_by_id:
                    out.append(Finding(
                        code="WIZ401",
                        severity=Severity.WARNING,
                        location=Location(entity="FlowNode", id=node_uuid, field="tag_list"),
                        message=f"Node references unknown tag category {cat_id!r}.",
                    ))
                    continue
                for row in cat.get("bizTagPropertyDTOS") or []:
                    if not isinstance(row, dict):
                        continue
                    vid = str(row.get("id", ""))
                    known = val_by_id.get(vid)
                    if known is None:
                        out.append(Finding(
                            code="WIZ401",
                            severity=Severity.WARNING,
                            location=Location(
                                entity="FlowNode", id=node_uuid, field="tag_list"),
                            message=f"Node references unknown tag value {vid!r}.",
                        ))
                    elif known.tag_id != cat_id or ("tagId" in row and str(row["tagId"]) != cat_id):
                        out.append(Finding(
                            code="WIZ401",
                            severity=Severity.WARNING,
                            location=Location(
                                entity="FlowNode", id=node_uuid, field="tag_list"),
                            message=(f"Tag value {vid!r} does not belong to "
                                     f"category {cat_id!r}."),
                        ))

    # WIZ402: kbTag category references
    kb_tag = _decode(wf.raw.get("kbTag"))
    if isinstance(kb_tag, list):
        for cid in kb_tag:
            sid = str(cid)
            if sid not in cat_by_id:
                out.append(Finding(
                    code="WIZ402",
                    severity=Severity.WARNING,
                    location=Location(entity="WizFile", id=None, field="kbTag"),
                    message=f"kbTag references unknown tag category {sid!r}.",
                ))
    return out
