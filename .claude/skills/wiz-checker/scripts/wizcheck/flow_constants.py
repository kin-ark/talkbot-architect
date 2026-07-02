"""Flow-encoding constants discovered from real WIZ exports (Task 1 probe).

NODE_TYPE_MAP maps the raw integer `type` field to a stable node-type name.
Values confirmed by running probe_flow.py against speech2572824560161596380.unpacked.json
and cross-referencing with Product Guidance §2.2 (Talk, Variable Assignment,
Conditional Judgment, Exit, LLM node types).

IMPORTANT — parser mismatch:
  The checker parser (wizcheck.parser) reads details[<uuid>].canvas.component.props.list
  entries as FlowNodes. Those entries are the component navigation pick-list
  (tree view items) and carry NO 'type' field — FlowNode.raw.get("type") == None.

  The REAL per-node type lives at the envelope level:
    details[<uuid>].type                          (authoritative)
    details[<uuid>].data.type                     (same value, redundant)
    details[<uuid>].canvas.component.props.type   (same value, redundant)

  Downstream FlowModel work (Tasks 2-6) MUST read envelope-level types
  directly from BizSpeechComponent.details[uuid], not from parser FlowNode.raw.
"""
from __future__ import annotations

# Probe output (59 total envelopes across 16 components):
#
#   type=1   n=11  Talk nodes (Greeting, Pitch, Convincer, etc.)
#             - Confirmed §2.2.2 Talk Node: has dialog_list, all_client_intent,
#               speakType, node_repetition, allow_jump_knowledges.
#             - value_assignment also appears on type=1 (inline VA inside Talk).
#
#   type=2   n=10  Exit nodes ("Exit Node", "Negative", "Wrong person", etc.)
#             - Confirmed §2.2.5 Exit Node: has dialog_list (closing script),
#               appoint_node_id="" (empty → hang up), is_transfer=0.
#             - No appoint_node_id routing — these are terminal hang-up exits.
#
#   type=4   n=20  "Go To" transition nodes (e.g. "Go To Pitch", "Go To
#               Unclassified Closing").
#             - Sub-type of Exit behaviour (§2.2.5 "Go to specific component"):
#               appoint_node_id = target componentUuid (always populated).
#               specificComponentName = human-readable target name.
#             - 20 / 20 have appoint_node_id populated (verified).
#
#   type=5   n=3   Inline Talk nodes used to bridge flow ("Continue the call").
#             - Has dialog_list (one-line script), appoint_node_id="",
#               transfer_type="", agent_group="".
#             - Not a standalone node type in §2.2; likely a legacy Talk variant
#               used as an in-flow continuation stub.
#             - No LLM markers found in this export — type 5 is NOT LLM here.
#               LLM nodes (§2.2.6) may appear in other exports; integer TBD.
#
#   type=7   n=8   Conditional Judgment nodes (§2.2.4).
#             - Confirmed: has 'branch' (list of conditions), 'branchList'
#               (human names), 'client_intent'.
#             - 'branch' key ONLY appears on type=7 nodes (confirmed).
#
#   type=8   n=1   "Go To KB" node ("Go To KB Busy").
#             - Has appoint_knowledge_id (KB id), no appoint_node_id.
#             - Sub-type of Exit behaviour targeting a Knowledge Base directly
#               (§2.2.5 "Go to specific knowledge base").
#
#   type=10  n=6   Variable Assignment nodes (§2.2.3).
#             - Confirmed: has value_assignment (list of var→func mappings),
#               sentence (optional script), node_function, node_variables.

NODE_TYPE_MAP: dict[int, str] = {
    1: "talk",
    2: "exit",
    4: "goto_component",    # Exit sub-type: jump to a specific component
    5: "talk_continue",     # Inline Talk continuation stub (bridge node)
    7: "conditional",
    8: "goto_kb",           # Exit sub-type: jump to a specific knowledge base
    9: "talk_goto",         # Exit sub-type: speak then jump to a specific component
    10: "variable_assignment",
    11: "nested_component", # Nested/sub-component node (contains a child component)
    13: "transfer",         # Transfer-to-human node (distinct from type-2 exit/hangup)
    # LLM node type integer not observed in this export; §2.2.6 describes it
    # as a distinct node type — add here once seen in an LLM-enabled export.
}

UNKNOWN_NODE_TYPE = "unknown"

# Key on a node's data dict whose value is the list of answer/condition branches.
# Only type=7 (Conditional Judgment) carries this key (confirmed: all 8 type-7
# nodes have it; zero type-1/2/4/5/8/10 nodes have it).
BRANCH_KEY = "branch"

# Key on a "go-to" node's data dict describing the target component UUID.
# 'appoint_node_id' is the routing key for type=4 (goto_component) and type=5
# nodes. Type=2 (exit/hang-up) nodes also have appoint_node_id but it is always
# empty string (""). Type=8 (goto_kb) uses 'appoint_knowledge_id' instead.
# The brief's placeholder "nextStep" was NOT found in any real envelope.
EXIT_NEXTSTEP_KEY = "appoint_node_id"

# Additional routing key for KB-jump nodes (type=8).
EXIT_KB_KEY = "appoint_knowledge_id"
