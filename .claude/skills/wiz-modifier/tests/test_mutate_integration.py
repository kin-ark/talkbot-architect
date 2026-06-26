"""End-to-end integration test: build → mutate sequence → checker re-parse.

Task 10 Step 1 — FM-T10.

The test builds a multi-component bot via the builder, applies a 5-op sequence:
  1. rename-node  (label + prompt on a talk node in comp 0)
  2. rewire-edge  (repoint a branch to a different node in comp 0)
  3. delete-edge  (drop a branch route, making comp 0 incomplete)
  4. complete-component  (repairs comp 0 — adds Exit, wires all dangling branches)
  5. delete-node  (removes a node from comp 1)
  6. move-node    (cross-component: moves a node from comp 1 → comp 0)

Then re-parses the mutated export through the checker and asserts structural
invariants:

  I-1  Every route endpoint (source node + target node) in every component's
       decoded ``routes`` exists in that component's ``details``.
  I-2  Every uuid listed in a component's ``inboundPorts`` exists in that
       component's ``details``.
  I-3  Terminal nodes (type 2 exit, type 13 transfer, type-4 goto, exit_port)
       have ``routes[uuid] == {}`` (empty mapping — no outbound routes).
  I-4  No duplicate ``SentenceCutSpeech`` row ``id`` within a single component.
  I-5  The checker ``parse_dict`` + ``run_all_checks`` runs without raising;
       the return value is a list (may be non-empty — findings are OK).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Cross-skill sys.path setup (same pattern as test_mutate_ops.py)
# ---------------------------------------------------------------------------

_SKILL_ROOT = Path(__file__).resolve().parents[2]
_BUILDER_SCRIPTS = str(_SKILL_ROOT / "wiz-builder" / "scripts")
_CHECKER_SCRIPTS = str(_SKILL_ROOT / "wiz-checker" / "scripts")
for _p in (_BUILDER_SCRIPTS, _CHECKER_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizbuilder.ids import IdMinter  # noqa: E402
from wizcheck.checks import run_all_checks  # noqa: E402
from wizcheck.parser import parse_dict  # noqa: E402
from wizmodifier.floweditor import FlowEditor  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import mutate  # noqa: E402
from wizmodifier.ops._bsc import get_components  # noqa: E402

FIXTURES = _SKILL_ROOT / "wiz-builder" / "tests" / "fixtures"
MINTER = IdMinter(manifest_hash="integration-test")


# ---------------------------------------------------------------------------
# Build helper
# ---------------------------------------------------------------------------


def _build_multi(tmp_path: Path) -> dict:
    """Compile manifest_multi_canvas.yaml → parsed export dict."""
    out = tmp_path / "speech.json"
    compile_manifest(FIXTURES / "manifest_multi_canvas.yaml", out)
    return json.loads(out.read_text(encoding="utf-8"))


def _bundle(doc: dict) -> InputBundle:
    return InputBundle(data=dict(doc), speech_name="s.json")


def _uw(v):
    """Decode an escaped-JSON string (or pass through if already decoded)."""
    return json.loads(v) if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Structural invariant helpers
# ---------------------------------------------------------------------------


def _check_route_endpoints(bundle: InputBundle) -> list[str]:
    """Return a list of violation strings for invariant I-1.

    For every component, for every route entry, check that:
      - the source node uuid (the routes key) exists in details
      - every edge target uuid exists in details
    """
    violations: list[str] = []
    for comp in get_components(bundle):
        name = comp.get("name", "<unknown>")
        details = _uw(comp.get("details") or "{}")
        routes = _uw(comp.get("routes") or "{}")
        for src_uuid, port_map in routes.items():
            if not isinstance(port_map, dict):
                continue
            if src_uuid and src_uuid not in details:
                violations.append(
                    f"comp {name!r}: routes key {src_uuid!r} not in details"
                )
            for edge in port_map.values():
                tgt = (edge.get("target") or {}).get("uuid")
                if tgt and tgt not in details:
                    violations.append(
                        f"comp {name!r}: route edge target {tgt!r} not in details"
                        f" (src={src_uuid!r})"
                    )
    return violations


def _check_inbound_ports(bundle: InputBundle) -> list[str]:
    """Return violation strings for invariant I-2.

    Every uuid in inboundPorts must exist in the same component's details.
    """
    violations: list[str] = []
    for comp in get_components(bundle):
        name = comp.get("name", "<unknown>")
        details = _uw(comp.get("details") or "{}")
        inbound = _uw(comp.get("inboundPorts") or "[]")
        for entry in inbound:
            u = entry.get("uuid")
            if u and u not in details:
                violations.append(
                    f"comp {name!r}: inboundPorts uuid {u!r} not in details"
                )
    return violations


def _check_terminal_empty_routes(bundle: InputBundle) -> list[str]:
    """Return violation strings for invariant I-3.

    Terminal nodes (type 2, type 13, and type-4 goto/exit_port) must have
    routes[uuid] == {} (empty dict — no outbound routes).

    Type-4 exit_port: both appoint_node_id and specificComponentName are empty.
    Type-4 goto: appoint_node_id is non-empty.
    Both are terminal (no out-routes); we check routes[uuid] == {} for all type 2/13/4.
    """
    violations: list[str] = []
    for comp in get_components(bundle):
        name = comp.get("name", "<unknown>")
        details = _uw(comp.get("details") or "{}")
        routes = _uw(comp.get("routes") or "{}")
        for uuid, node in details.items():
            ntype = node.get("type")
            if ntype in (2, 13, 4):
                port_map = routes.get(uuid, {})
                if port_map:
                    violations.append(
                        f"comp {name!r}: terminal node {uuid!r} (type={ntype})"
                        f" has non-empty routes: {list(port_map.keys())}"
                    )
    return violations


def _check_no_duplicate_scs_ids(bundle: InputBundle) -> list[str]:
    """Return violation strings for invariant I-4.

    Within a single component, no two SentenceCutSpeech rows may share the
    same ``id`` value.
    """
    violations: list[str] = []
    scs: list[dict] = _uw(bundle.data.get("SentenceCutSpeech") or "[]")
    # Group by componentUuid.
    from_comp: dict[str, list[str]] = {}
    for row in scs:
        comp_uuid = row.get("componentUuid", "")
        row_id = row.get("id", "")
        from_comp.setdefault(comp_uuid, []).append(row_id)
    for comp_uuid, ids in from_comp.items():
        seen: set[str] = set()
        for rid in ids:
            if rid in seen:
                violations.append(
                    f"componentUuid {comp_uuid!r}: duplicate SCS id {rid!r}"
                )
            seen.add(rid)
    return violations


def _assert_all_invariants(bundle: InputBundle) -> None:
    """Assert all four structural invariants; aggregate violations and fail once."""
    all_violations: list[str] = []
    all_violations += _check_route_endpoints(bundle)
    all_violations += _check_inbound_ports(bundle)
    all_violations += _check_terminal_empty_routes(bundle)
    all_violations += _check_no_duplicate_scs_ids(bundle)
    assert not all_violations, (
        f"{len(all_violations)} structural invariant violation(s):\n"
        + "\n".join(f"  {v}" for v in all_violations)
    )


# ---------------------------------------------------------------------------
# Main integration test
# ---------------------------------------------------------------------------


def test_mutate_sequence_round_trip(tmp_path: Path):
    """Build multi-canvas bot, apply 6-op sequence, assert structural invariants.

    Op sequence:
      1. rename-node  — greet-root in comp 0: new label + new prompt.
      2. rewire-edge  — repoint greet-root's Unclassified branch from greet-pitch
                        to itself (the only other node); actually we rewire it to
                        the entry node (greet-root itself is entry) — we rewire
                        greet-pitch's (type-1, no outbound) Unclassified port once
                        we ensure it has one, OR more cleanly: we add complete-component
                        first on comp 1 to get an exit, then rewire greet-root's
                        Unclassified to that exit.
                        Concretely: run complete-component on comp 0 first to get an
                        exit and wired Unclassified, then rewire-edge on greet-root
                        Unclassified → the new exit node.
      3. delete-edge  — drop greet-pitch's Unclassified route in comp 0 (if present),
                        making comp 0 incomplete again (or just drop greet-root's
                        rewired Unclassified to make it incomplete).
      4. complete-component — repairs comp 0 again.
      5. delete-node  — removes close-root from comp 1 (the only node → comp 1 empty
                        after this, which is fine for the structural check).
      6. move-node    — move greet-pitch (now in comp 0 after all edits) to comp 1.
                        If greet-pitch was already deleted by a prior cascade, we
                        skip this op (or move a different node).

    Invariants checked after the full sequence:
      I-1  No route endpoint references a missing node.
      I-2  No inboundPorts uuid references a missing node.
      I-3  Terminal nodes have empty routes.
      I-4  No duplicate SCS id within a component.
      I-5  parse_dict + run_all_checks returns a list without raising.
    """
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    comps = get_components(bundle)
    assert len(comps) >= 2, "Expected at least 2 components from manifest_multi_canvas"

    # Identify nodes in comp 0 and comp 1
    fe0 = FlowEditor(comps[0])
    fe1 = FlowEditor(comps[1])
    details0 = dict(fe0.details)
    details1 = dict(fe1.details)

    comp1_name = comps[1]["name"]

    # greet-root: has outbound edges in comp 0 (the entry talk node)
    greet_root = next((u for u in details0 if fe0.out_edges(u)), None)
    assert greet_root is not None, "Expected an entry node with outbound edges in comp 0"

    # greet-pitch: no outbound edges initially in comp 0
    greet_pitch = next((u for u in details0 if not fe0.out_edges(u)), None)
    assert greet_pitch is not None, "Expected a terminal-ish talk node in comp 0"

    # close-root: node in comp 1
    close_root = next(iter(details1))
    assert close_root is not None, "Expected at least one node in comp 1"

    # ---------- Op 1: rename-node (greet-root, label + prompt) ----------
    mutate.rename_node(bundle, {
        "component": 0,
        "node": {"uuid": greet_root},
        "label": "intro_renamed",
        "prompt": "Selamat datang, ada yang bisa saya bantu?",
    }, MINTER)

    # Verify label + SCS updated
    comps_after = get_components(bundle)
    fe0_after = FlowEditor(comps_after[0])
    assert fe0_after.details[greet_root]["data"]["name"] == "intro_renamed"
    scs = _uw(bundle.data.get("SentenceCutSpeech") or "[]")
    scs_rows = [r for r in scs if r.get("id") == greet_root]
    assert scs_rows and scs_rows[0]["sentenceText"] == "Selamat datang, ada yang bisa saya bantu?"

    # ---------- Op 2: complete-component on comp 0 (ensures exit + all branches wired) ----------
    result_cc = mutate.complete_component(bundle, {"component": 0}, MINTER)
    assert "added_exit" in result_cc
    # After complete, find the exit node in comp 0
    comps_after = get_components(bundle)
    fe0_after = FlowEditor(comps_after[0])
    assert fe0_after.has_exit(), "complete-component must add an exit node"
    exit_uuid_comp0 = next(u for u, n in fe0_after.details.items() if n.get("type") == 2)

    # ---------- Op 3: rewire-edge — repoint greet-root's Unclassified to the exit ----------
    # Greet-root now has an Unclassified port (complete-component added it) that points at
    # greet-pitch. Rewire it to the exit node so the test exercises rewire-edge.
    mutate.rewire_edge(bundle, {
        "component": 0,
        "from": {"uuid": greet_root},
        "branch": "Unclassified",
        "to": {"uuid": exit_uuid_comp0},
    }, MINTER)

    # Verify the Unclassified edge now targets the exit
    comps_after = get_components(bundle)
    fe0_after = FlowEditor(comps_after[0])
    edges = dict(fe0_after.out_edges(greet_root))
    assert edges.get("Unclassified") == exit_uuid_comp0, (
        "rewire-edge must have repointed Unclassified to exit"
    )

    # ---------- Op 4: delete-edge — drop greet-root's Unclassified route ----------
    # This makes comp 0 incomplete again (Unclassified dangling).
    mutate.delete_edge(bundle, {
        "component": 0,
        "from": {"uuid": greet_root},
        "branch": "Unclassified",
    }, MINTER)

    # Verify route is gone
    comps_after = get_components(bundle)
    fe0_after = FlowEditor(comps_after[0])
    edges_after_del = dict(fe0_after.out_edges(greet_root))
    assert "Unclassified" not in edges_after_del, "delete-edge must remove the route"

    # ---------- Op 5: complete-component again — repairs comp 0 ----------
    mutate.complete_component(bundle, {"component": 0}, MINTER)
    comps_after = get_components(bundle)
    fe0_after = FlowEditor(comps_after[0])
    assert fe0_after.has_exit()
    assert fe0_after.unconnected_branches() == [], (
        "complete-component must wire all dangling branches"
    )

    # ---------- Op 6: delete-node — remove close-root from comp 1 ----------
    mutate.delete_node(bundle, {
        "component": 1,
        "node": {"uuid": close_root},
    }, MINTER)

    # close-root must be gone from comp 1
    comps_after = get_components(bundle)
    fe1_after = FlowEditor(comps_after[1])
    assert close_root not in fe1_after.details, "delete-node must remove node from details"

    # ---------- Op 7: move-node — move greet-pitch from comp 0 to comp 1 ----------
    # greet-pitch is still in comp 0 (it was not deleted). Move it across.
    result_move = mutate.move_node(bundle, {
        "node": {"uuid": greet_pitch},
        "to_component": comp1_name,
    }, MINTER)
    assert result_move["moved"] == greet_pitch

    # greet-pitch must be in comp 1 now
    comps_after = get_components(bundle)
    fe0_final = FlowEditor(comps_after[0])
    fe1_final = FlowEditor(comps_after[1])
    assert greet_pitch not in fe0_final.details, "Moved node must be gone from comp 0"
    assert greet_pitch in fe1_final.details, "Moved node must be in comp 1"

    # ---------- Structural invariant checks ----------
    _assert_all_invariants(bundle)

    # ---------- Invariant I-5: checker parse + run_all_checks (no crash) ----------
    wf = parse_dict(bundle.data)
    findings = run_all_checks(wf)
    assert isinstance(findings, list), "run_all_checks must return a list"
    # Log finding count for visibility (non-zero findings are OK at this integration level)
    error_findings = [f for f in findings if getattr(f, "level", "").lower() == "error"]
    # We don't assert zero errors — the checker may flag incomplete components or
    # other issues in a partially-edited export. What we assert is that it doesn't
    # crash and returns a list.
    _ = error_findings  # available for debugging if test fails


def test_invariant_helpers_detect_violations(tmp_path: Path):
    """Negative test: manually corrupt a bundle and confirm the helpers catch it."""
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    # Run complete-component on all comps so the invariants hold first.
    mutate.complete_component(bundle, {"component": 0}, MINTER)
    mutate.complete_component(bundle, {"component": 1}, MINTER)

    # Confirm no violations before corruption
    assert _check_route_endpoints(bundle) == []
    assert _check_inbound_ports(bundle) == []
    assert _check_terminal_empty_routes(bundle) == []
    assert _check_no_duplicate_scs_ids(bundle) == []

    # Corrupt: inject a route that targets a non-existent node in comp 0
    from wizmodifier import codec  # noqa: PLC0415
    from wizmodifier.ops._bsc import get_components, set_components  # noqa: PLC0415
    comps = get_components(bundle)
    routes0 = _uw(comps[0].get("routes") or "{}")
    details0 = _uw(comps[0].get("details") or "{}")
    some_node = next(iter(details0))
    some_port_id = "ffff0000-0000-0000-0000-000000000000"
    fake_target = "dead0000-0000-0000-0000-000000000000"
    routes0.setdefault(some_node, {})[some_port_id] = {
        "source": {"type": 1, "uuid": some_port_id},
        "target": {"type": 1, "uuid": fake_target},
    }
    comps[0]["routes"] = codec.encode(routes0)
    set_components(bundle, comps)

    violations = _check_route_endpoints(bundle)
    assert any(fake_target in v for v in violations), (
        "Helper must detect the injected bad route endpoint"
    )
