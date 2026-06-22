"""Inspect a real WIZ export to discover node-type ints and routing fields.

Run:  python dashboard/backend/scripts/probe_flow.py <speech*.json|unpacked.json>
Prints distinct node `type` ints with sample labels, and the keys present on
nodes that carry branches / exit next-step info.

NOTE (Task 1 finding): The checker parser (wizcheck.parser) reads
canvas.component.props.list entries from each envelope, which are the
component navigation pick-list (tree view items — e.g. "1. Greeting",
"8. Positive Closing"). These nav-list entries do NOT carry a 'type' field,
so FlowNode.raw.get("type") returns None for every node.

The REAL per-node type lives at the ENVELOPE level:
  details[<uuid>].type                          (int, e.g. 4)
  details[<uuid>].data.type                     (same int)
  details[<uuid>].canvas.component.props.type   (same int)

Section A below uses the parser path (confirms the None mismatch).
Section B reads envelope-level types directly and is the authoritative output.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import add_skill_paths  # noqa: E402

add_skill_paths()
from wizcheck.parser import parse_file  # noqa: E402


def _probe_via_parser(path: str) -> None:
    """Section A: probe using checker parser FlowNode objects.

    Expected result: type=None for all nodes because parser reads nav-list
    entries, not the actual flow-node envelopes.
    """
    wf = parse_file(path)
    type_counts: Counter = Counter()
    type_samples: dict = defaultdict(list)
    keys_on_nodes: Counter = Counter()
    for comp in wf.components.values():
        for node in comp.details.flow_nodes.values():
            t = node.raw.get("type")
            type_counts[t] += 1
            if len(type_samples[t]) < 3:
                type_samples[t].append(node.label)
            for k in node.raw:
                keys_on_nodes[k] += 1
    print("=== SECTION A: types via parser FlowNode.raw (expect all None) ===")
    for t, c in type_counts.most_common():
        print(f"  type={t!r:5}  n={c:4}  e.g. {type_samples[t]}")
    print()
    print("=== SECTION A: keys on parser FlowNode.raw ===")
    for k, c in keys_on_nodes.most_common():
        print(f"  {k}  ({c})")
    print()


def _probe_envelope_level(path: str) -> None:
    """Section B: probe envelope-level types directly from raw JSON.

    This is the authoritative view — reads details[<uuid>].type directly.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # BizSpeechComponent is a list in the unpacked export.
    bsc_raw = data.get("BizSpeechComponent", [])
    if isinstance(bsc_raw, str):
        bsc_raw = json.loads(bsc_raw)

    type_counts: Counter = Counter()
    type_samples: dict = defaultdict(list)
    all_data_keys: Counter = Counter()
    # Track which data keys appear on each type
    type_data_keys: dict = defaultdict(Counter)

    for comp in bsc_raw:
        details = comp.get("details", {})
        if isinstance(details, str):
            details = json.loads(details) if details.strip() else {}
        if not isinstance(details, dict):
            continue
        for uuid, envelope in details.items():
            if not isinstance(envelope, dict):
                continue
            t = envelope.get("type")
            name = envelope.get("name", "")
            type_counts[t] += 1
            if len(type_samples[t]) < 5:
                type_samples[t].append(name)
            d = envelope.get("data", {})
            if isinstance(d, dict):
                for k in d:
                    all_data_keys[k] += 1
                    type_data_keys[t][k] += 1

    print("=== SECTION B: envelope-level type ints (REAL node types) ===")
    for t, c in sorted(type_counts.items(), key=lambda x: (x[0] is None, x[0] or 0)):
        print(f"  type={t!r:5}  n={c:4}  e.g. {type_samples[t]}")
    print()

    print("=== SECTION B: per-type distinctive data keys ===")
    for t in sorted(type_counts, key=lambda x: (x is None, x or 0)):
        keys = type_data_keys[t]
        # Highlight keys that appear on this type but not (or rarely) on others
        print(f"  type={t!r}:")
        for k, c in keys.most_common(8):
            print(f"    {k}  ({c})")
    print()

    print("=== SECTION B: all data keys across all envelopes ===")
    for k, c in all_data_keys.most_common():
        print(f"  {k}  ({c})")


def main(path: str) -> None:
    _probe_via_parser(path)
    _probe_envelope_level(path)


if __name__ == "__main__":
    main(sys.argv[1])
