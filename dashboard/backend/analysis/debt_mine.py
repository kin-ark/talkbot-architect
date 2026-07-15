"""Repeatable miner: extract ranked debt-collection patterns from the corpus.

Reads real WIZ.AI export ZIPs (git-ignored `talkbot/Debt Collection/`) through the
checker IR and emits one PII-scrubbed, deterministic JSON. Dev/refresh tool; the JSON
it produces is the durable tracked artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

# Put the checker on sys.path exactly like agents.py does.
_BACKEND = Path(__file__).resolve().parents[1]
_CHECKER = _BACKEND.parents[1] / ".claude" / "skills" / "wiz-checker" / "scripts"
if str(_CHECKER) not in sys.path:
    sys.path.insert(0, str(_CHECKER))

from wizcheck.parser import parse_dict  # noqa: E402

_AMOUNT = re.compile(r"Rp\.?\s?[\d.,]+", re.IGNORECASE)
_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_DIGITS = re.compile(r"\d{6,}")           # phone / VA / account / long id
_SHORTNUM = re.compile(r"\b\d{3,5}\b")     # medium numbers (amounts without Rp)

_STAGE_PATTERNS = [
    # Specific dpd/ptp patterns first: the predue pattern's bare `d-?1` alt is
    # broad enough to false-match inside e.g. "DPD1-5", so it must be checked
    # last (fallback), not first.
    ("dpd0", re.compile(r"dpd\s*0\b", re.IGNORECASE)),
    ("dpd1_5", re.compile(r"dpd\s*1[\s._-]*5", re.IGNORECASE)),
    ("dpd6_30", re.compile(r"dpd\s*(6|10)[\s._-]*(30|10)", re.IGNORECASE)),
    ("overdue_90", re.compile(r"overdue.*90|90\+|dpd\s*(60|90)", re.IGNORECASE)),
    ("ptp_reminder", re.compile(r"ptp", re.IGNORECASE)),
    ("predue_d1", re.compile(r"predue|pre-?due|d-?1", re.IGNORECASE)),
]


def scrub(text: str) -> str:
    if not text:
        return text or ""
    t = _AMOUNT.sub("{amount}", text)
    t = _EMAIL.sub("{email}", t)
    t = _DATE.sub("{date}", t)
    t = _DIGITS.sub("{number}", t)
    t = _SHORTNUM.sub("{number}", t)
    return t


def stage_from_name(zip_name: str) -> str:
    for label, pat in _STAGE_PATTERNS:
        if pat.search(zip_name):
            return label
    return "mixed"


def mine_bot(data: dict, stage: str) -> dict:
    """Parse ONE export dict into a scrubbed per-bot record."""
    wf = parse_dict(data)
    fm = wf.flow_model

    intents = []
    for it in wf.intents.values():
        is_init = int((it.raw or {}).get("isInit", 0) or 0)
        intents.append({
            "name": it.name,
            "keywords": [scrub(k) for k in it.keywords],
            "user_responses": [scrub(u) for u in it.user_responses],
            "is_user": is_init == 1,   # intents: isInit 1 = user-created
        })

    kbs = []
    for kb in (fm.knowledge_bases if fm else []):
        answers = [scrub((a or {}).get("text", "")) for a in getattr(kb, "answers", [])]
        kbs.append({
            "title": kb.title,
            "intent_names": list(getattr(kb, "intent_names", [])),
            "answers": [a for a in answers if a],
            "multi_round": bool(getattr(kb, "multi_round", None)),
            "is_user": bool(getattr(kb, "is_user_created", False)),
        })

    # category per component uuid (from IR, not flow_model)
    cat_by_uuid = {str(u): c.category for u, c in wf.components.items()}

    scripts, engines = [], []
    for comp in (fm.components if fm else []):
        for node in comp.nodes.values():
            nt = node.node_type
            if nt == "talk" and node.text:
                scripts.append({"role": _role_of(node, comp), "text": scrub(node.text)})
            elif nt == "conditional":
                var = ((node.data or {}).get("branch") or [{}])
                engines.append({"kind": "conditional",
                                "branches": [scrub(str(b.get("name", ""))) for b in var]})
            elif nt == "variable_assignment":
                va = (node.data or {}).get("value_assignment") or []
                engines.append({"kind": "assign",
                                "vars": [(v.get("variable") or {}).get("name", "") for v in va]})

    tags = []
    for cat in wf.tags:
        tags.append({"category": cat.name,
                     "values": [v.value for v in getattr(cat, "values", [])]})

    return {"stage": stage, "intents": intents, "kbs": kbs,
            "scripts": scripts, "engines": engines, "tags": tags,
            "categories": sorted(set(cat_by_uuid.values()))}


def _role_of(node, comp) -> str:
    """Best-effort script-role classifier by entry position + branch labels."""
    if comp.entry_uuid == node.uuid:
        return "greeting"
    labels = {b.label.lower() for b in node.branches}
    if {"positive"} & labels:
        return "convincer"
    if any("ptp" in lb or "janji" in lb for lb in labels):
        return "ptp_capture"
    if not node.branches:
        return "closing"
    return "inform"


def _rank(items_by_bot: list[list], key_fn, n_bots: int) -> list[dict]:
    """Count how many bots each distinct key appears in -> ranked list with pct."""
    seen = [{key_fn(x) for x in items} for items in items_by_bot]
    counts: dict = defaultdict(int)
    repr_item: dict = {}
    for bot_items, keyset in zip(items_by_bot, seen):
        for x in bot_items:
            k = key_fn(x)
            repr_item.setdefault(k, x)
        for k in keyset:
            counts[k] += 1
    ranked = []
    for k, c in counts.items():
        item = dict(repr_item[k])
        item["count"] = c
        item["pct"] = round(c / n_bots, 3) if n_bots else 0.0
        ranked.append((k, item))
    # Total order: the key_fn value `k` is unique per entry, so str(k) is a
    # deterministic tie-break independent of dict/set iteration (PYTHONHASHSEED).
    ranked.sort(key=lambda t: (-t[1]["count"], str(t[0])))
    return [item for _, item in ranked]


def aggregate(records: list[dict]) -> dict:
    n = len(records)
    intents = _rank([r["intents"] for r in records], lambda x: x["name"], n)
    kbs = _rank([r["kbs"] for r in records], lambda x: x["title"], n)
    scripts = _rank([r["scripts"] for r in records], lambda x: (x["role"], x["text"]), n)
    engines = _rank(
        [r["engines"] for r in records],
        lambda x: (x["kind"], tuple(x.get("branches") or x.get("vars") or [])),
        n,
    )
    tags = _rank([r["tags"] for r in records], lambda x: x["category"], n)

    # stage_deltas: which intents/kbs/tone markers appear per stage
    stage_deltas = []
    by_stage: dict = defaultdict(list)
    for r in records:
        by_stage[r["stage"]].append(r)
    for stage, recs in sorted(by_stage.items()):
        s_intents = _rank([r["intents"] for r in recs], lambda x: x["name"], len(recs))
        stage_deltas.append({"stage": stage, "bots": len(recs),
                             "top_intents": [i["name"] for i in s_intents[:12]]})

    # objection_map: user-created intents -> the KB titles that name them as triggers
    objection_map = []
    for it in intents:
        if not it.get("is_user"):
            continue
        handlers = sorted({kb["title"] for r in records for kb in r["kbs"]
                           if it["name"] in kb.get("intent_names", [])})
        objection_map.append({"intent": it["name"], "handled_by": handlers, "count": it["count"]})

    return {
        "meta": {"bots_parsed": n, "bots_total": n,
                 "generated_note": "Mined from real deployed WIZ.AI debt-collection bots (IDN). PII scrubbed."},
        "intents": intents, "kbs": kbs, "script_archetypes": scripts,
        "flow_engines": engines, "stage_deltas": stage_deltas,
        "objection_map": objection_map, "tag_patterns": tags,
    }


def _load_export_from_zip(zpath: Path) -> dict | None:
    try:
        with zipfile.ZipFile(zpath) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".json") and "speech" in n.lower()]
            if not names:
                names = [n for n in z.namelist() if n.lower().endswith(".json")]
            if not names:
                return None
            return json.loads(z.read(names[0]).decode("utf-8"))
    except Exception:
        return None


def run(corpus_dir: str, out_path: str) -> dict:
    cdir = Path(corpus_dir)
    records, errors = [], []
    for zpath in sorted(cdir.glob("*.zip")):
        data = _load_export_from_zip(zpath)
        if data is None:
            errors.append(zpath.name)
            continue
        try:
            records.append(mine_bot(data, stage_from_name(zpath.name)))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{zpath.name}: {e}")
    corpus = aggregate(records)
    corpus["meta"]["bots_total"] = len(list(cdir.glob("*.zip")))
    corpus["meta"]["parse_errors"] = errors
    text = json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True)
    out = Path(out_path)
    fd, tmp = tempfile.mkstemp(dir=str(out.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, out)
    print(f"parsed {len(records)} of {corpus['meta']['bots_total']} -> {out}")
    return corpus


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="talkbot/Debt Collection")
    ap.add_argument("--out", default=str(_BACKEND / "playbooks" / "debt_collection.corpus.json"))
    args = ap.parse_args()
    run(args.corpus, args.out)


if __name__ == "__main__":
    main()
