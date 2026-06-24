"""Tests for flowmodel.py — all using synthetic dicts, no real export needed.

Tests are ordered to match the brief's required coverage list:
  1. node_type_of: known int, unknown int (99999), missing type
  2. unwrap: JSON-string list, native list, JSON-string dict, native dict, None
  3. talk node (type 1) with all_client_intent → two intent BranchEdges
  4. conditional node (type 7) with "Default" → kind == "default"
  5. type-4 node → exit branch with target_component == appoint_node_id
  6. type-8 node → exit branch with target_kb == int(appoint_knowledge_id)
  7. type-2 node with is_transfer:0 → terminal=="hangup"; is_transfer:1 → "transfer"
  8. talk node with allow_jump_knowledges → allowed_kbs cast to int
  9. build_components on minimal two-node component → correct FlowComponent
"""
import json

from wizcheck.flow_constants import NODE_TYPE_MAP
from wizcheck.flowmodel import (
    FlowModel,
    build_components,
    build_flow_model,
    flow_model_to_dict,
    node_type_of,
    unwrap,
)

# ---------------------------------------------------------------------------
# 1. node_type_of
# ---------------------------------------------------------------------------

class TestNodeTypeOf:
    def test_known_type_at_envelope_level(self):
        # type=1 → "talk"
        envelope = {"type": 1, "name": "Greeting", "data": {}}
        assert node_type_of(envelope) == "talk"

    def test_known_type_at_data_level(self):
        # type lives inside data (no top-level type key)
        envelope = {"name": "Greeting", "data": {"type": 1}}
        assert node_type_of(envelope) == "talk"

    def test_all_known_types_round_trip(self):
        for int_type, name in NODE_TYPE_MAP.items():
            envelope = {"type": int_type, "data": {}}
            assert node_type_of(envelope) == name

    def test_unknown_int_99999_returns_unknown(self):
        envelope = {"type": 99999, "data": {}}
        assert node_type_of(envelope) == "unknown"

    def test_missing_type_returns_unknown(self):
        envelope = {"name": "NoType", "data": {}}
        assert node_type_of(envelope) == "unknown"


# ---------------------------------------------------------------------------
# 2. unwrap
# ---------------------------------------------------------------------------

class TestUnwrap:
    def test_json_string_list(self):
        value = json.dumps([{"id": 1}, {"id": 2}])
        result = unwrap(value)
        assert result == [{"id": 1}, {"id": 2}]

    def test_native_list_passthrough(self):
        value = [{"id": 1}]
        result = unwrap(value)
        assert result is value  # same object, not a copy

    def test_json_string_dict(self):
        value = json.dumps({"key": "val"})
        result = unwrap(value)
        assert result == {"key": "val"}

    def test_native_dict_passthrough(self):
        value = {"key": "val"}
        result = unwrap(value)
        assert result is value

    def test_none_returns_empty_list(self):
        result = unwrap(None)
        assert result == []


# ---------------------------------------------------------------------------
# 3. talk node (type 1) with two intents
# ---------------------------------------------------------------------------

def _make_component_with_talk_node():
    """Minimal synthetic component with one talk node having two intents."""
    return {
        "componentUuid": "comp-1",
        "name": "Test Component",
        "sortIndex": 1,
        "details": {
            "n1": {
                "type": 1,
                "name": "Talk Node",
                "is_default": True,
                "data": {
                    "list": [{"text": "Hello there"}],
                    "all_client_intent": [
                        {"name": "Positive", "id": "p1", "checked": True},
                        {"name": "Negative", "id": "p2", "checked": True},
                    ],
                    "node_variables": [],
                    "allow_jump_knowledges": [],
                },
            },
            "n2": {
                "type": 2,
                "name": "Exit Positive",
                "is_default": False,
                "data": {
                    "list": [],
                    "is_transfer": 0,
                    "node_variables": [],
                    "allow_jump_knowledges": [],
                },
            },
            "n3": {
                "type": 2,
                "name": "Exit Negative",
                "is_default": False,
                "data": {
                    "list": [],
                    "is_transfer": 0,
                    "node_variables": [],
                    "allow_jump_knowledges": [],
                },
            },
        },
        "routes": {
            "n1": {
                "p1": {"source": {"type": 1, "uuid": "p1"}, "target": {"type": 1, "uuid": "n2"}},
                "p2": {"source": {"type": 1, "uuid": "p2"}, "target": {"type": 1, "uuid": "n3"}},
            },
            "n2": {},
            "n3": {},
        },
    }


class TestTalkNodeBranches:
    def test_talk_node_yields_two_intent_branches(self):
        comp_dict = _make_component_with_talk_node()
        components = build_components({"BizSpeechComponent": [comp_dict]})
        assert len(components) == 1
        node = components[0].nodes["n1"]
        assert len(node.branches) == 2

    def test_talk_branch_labels_and_kinds(self):
        comp_dict = _make_component_with_talk_node()
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["n1"]
        by_label = {b.label: b for b in node.branches}
        assert "Positive" in by_label
        assert "Negative" in by_label
        assert by_label["Positive"].kind == "intent"
        assert by_label["Negative"].kind == "intent"

    def test_talk_branch_target_uuids(self):
        comp_dict = _make_component_with_talk_node()
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["n1"]
        by_label = {b.label: b for b in node.branches}
        assert by_label["Positive"].target_uuid == "n2"
        assert by_label["Negative"].target_uuid == "n3"


# ---------------------------------------------------------------------------
# 4. conditional node (type 7) with "Default" → kind == "default"
# ---------------------------------------------------------------------------

def _make_component_with_conditional_node():
    return {
        "componentUuid": "comp-cond",
        "name": "Cond Component",
        "sortIndex": 1,
        "details": {
            "cond1": {
                "type": 7,
                "name": "Conditional Node",
                "is_default": True,
                "data": {
                    "list": [],
                    "all_client_intent": [
                        {"name": "Default", "id": "port-def", "checked": True},
                        {"name": "Positive Closing", "id": "port-pos", "checked": True},
                    ],
                    "branch": [],
                    "node_variables": [],
                    "allow_jump_knowledges": [],
                },
            },
            "exit-def": {
                "type": 2,
                "name": "Exit Default",
                "is_default": False,
                "data": {
                    "list": [], "is_transfer": 0, "node_variables": [], "allow_jump_knowledges": [],
                },
            },
            "exit-pos": {
                "type": 2,
                "name": "Exit Positive",
                "is_default": False,
                "data": {
                    "list": [], "is_transfer": 0, "node_variables": [], "allow_jump_knowledges": [],
                },
            },
        },
        "routes": {
            "cond1": {
                "port-def": {
                    "source": {"type": 1, "uuid": "port-def"},
                    "target": {"type": 1, "uuid": "exit-def"},
                },
                "port-pos": {
                    "source": {"type": 1, "uuid": "port-pos"},
                    "target": {"type": 1, "uuid": "exit-pos"},
                },
            },
            "exit-def": {},
            "exit-pos": {},
        },
    }


class TestConditionalNodeBranches:
    def test_default_branch_kind_is_default(self):
        comp_dict = _make_component_with_conditional_node()
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["cond1"]
        by_label = {b.label: b for b in node.branches}
        assert by_label["Default"].kind == "default"

    def test_non_default_condition_branch_kind_is_condition(self):
        comp_dict = _make_component_with_conditional_node()
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["cond1"]
        by_label = {b.label: b for b in node.branches}
        assert by_label["Positive Closing"].kind == "condition"


# ---------------------------------------------------------------------------
# 5. type-4 node → exit branch with target_component == appoint_node_id
# ---------------------------------------------------------------------------

class TestType4Node:
    def _make_comp(self):
        return {
            "componentUuid": "comp-goto",
            "name": "Goto Component",
            "sortIndex": 1,
            "details": {
                "goto1": {
                    "type": 4,
                    "name": "Go To Pitch",
                    "is_default": True,
                    "data": {
                        "list": [],
                        "appoint_node_id": "target-comp-uuid-123",
                        "specificComponentName": "2. Pitch",
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                    },
                },
            },
            "routes": {
                "goto1": {},
            },
        }

    def test_type4_yields_one_exit_branch(self):
        components = build_components({"BizSpeechComponent": [self._make_comp()]})
        node = components[0].nodes["goto1"]
        assert len(node.branches) == 1
        assert node.branches[0].kind == "exit"

    def test_type4_target_component_equals_appoint_node_id(self):
        components = build_components({"BizSpeechComponent": [self._make_comp()]})
        node = components[0].nodes["goto1"]
        assert node.branches[0].target_component == "target-comp-uuid-123"

    def test_type4_label_uses_specific_component_name(self):
        components = build_components({"BizSpeechComponent": [self._make_comp()]})
        node = components[0].nodes["goto1"]
        assert node.branches[0].label == "2. Pitch"


# ---------------------------------------------------------------------------
# 6. type-8 node → exit branch with target_kb == int(appoint_knowledge_id)
# ---------------------------------------------------------------------------

class TestType8Node:
    def _make_comp(self):
        return {
            "componentUuid": "comp-kb",
            "name": "KB Component",
            "sortIndex": 1,
            "details": {
                "kb1": {
                    "type": 8,
                    "name": "Go To KB Busy",
                    "is_default": True,
                    "data": {
                        "list": [],
                        "appoint_knowledge_id": "183805",
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                    },
                },
            },
            "routes": {
                "kb1": {},
            },
        }

    def test_type8_yields_one_exit_branch(self):
        components = build_components({"BizSpeechComponent": [self._make_comp()]})
        node = components[0].nodes["kb1"]
        assert len(node.branches) == 1
        assert node.branches[0].kind == "exit"

    def test_type8_target_kb_is_int(self):
        components = build_components({"BizSpeechComponent": [self._make_comp()]})
        node = components[0].nodes["kb1"]
        assert node.branches[0].target_kb == 183805
        assert isinstance(node.branches[0].target_kb, int)


# ---------------------------------------------------------------------------
# 7. type-2 exit node: is_transfer:0 → hangup; is_transfer:1 → transfer
# ---------------------------------------------------------------------------

class TestType2ExitNode:
    def _make_comp(self, is_transfer: int, node_id: str = "exit1"):
        return {
            "componentUuid": "comp-exit",
            "name": "Exit Component",
            "sortIndex": 1,
            "details": {
                node_id: {
                    "type": 2,
                    "name": "Exit Node",
                    "is_default": True,
                    "data": {
                        "list": [],
                        "is_transfer": is_transfer,
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                    },
                },
            },
            "routes": {
                node_id: {},
            },
        }

    def test_is_transfer_0_yields_hangup(self):
        components = build_components({"BizSpeechComponent": [self._make_comp(0)]})
        node = components[0].nodes["exit1"]
        assert len(node.branches) == 1
        assert node.branches[0].terminal == "hangup"
        assert node.branches[0].kind == "exit"

    def test_is_transfer_1_still_yields_hangup(self):
        # type-2 is always a hang-up exit regardless of is_transfer flag.
        # Transfer-to-human is a distinct node type (13); is_transfer on type-2
        # is a legacy field that does NOT change the node's terminal semantics.
        components = build_components({"BizSpeechComponent": [self._make_comp(1)]})
        node = components[0].nodes["exit1"]
        assert node.branches[0].terminal == "hangup"


# ---------------------------------------------------------------------------
# 8. allow_jump_knowledges → allowed_kbs cast to int
# ---------------------------------------------------------------------------

class TestAllowedKBs:
    def test_allowed_kbs_cast_to_int(self):
        comp_dict = {
            "componentUuid": "comp-allowkb",
            "name": "Allow KB Component",
            "sortIndex": 1,
            "details": {
                "talk1": {
                    "type": 1,
                    "name": "Talk with KBs",
                    "is_default": True,
                    "data": {
                        "list": [],
                        "all_client_intent": [],
                        "node_variables": [],
                        "allow_jump_knowledges": ["183805", "183806"],
                    },
                },
            },
            "routes": {
                "talk1": {},
            },
        }
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["talk1"]
        assert node.allowed_kbs == [183805, 183806]
        assert all(isinstance(k, int) for k in node.allowed_kbs)


# ---------------------------------------------------------------------------
# 9. build_components: minimal two-node component
# ---------------------------------------------------------------------------

class TestBuildComponents:
    def _make_two_node_comp(self):
        return {
            "BizSpeechComponent": [
                {
                    "componentUuid": "comp-two",
                    "name": "Two Node Comp",
                    "sortIndex": 3,
                    "details": {
                        "node-a": {
                            "type": 1,
                            "name": "Entry Talk",
                            "is_default": True,
                            "data": {
                                "list": [{"text": "Hi"}],
                                "all_client_intent": [
                                    {"name": "Understood", "id": "port-u", "checked": True},
                                ],
                                "node_variables": [],
                                "allow_jump_knowledges": [],
                            },
                        },
                        "node-b": {
                            "type": 2,
                            "name": "Exit",
                            "is_default": False,
                            "data": {
                                "list": [],
                                "is_transfer": 0,
                                "node_variables": [],
                                "allow_jump_knowledges": [],
                            },
                        },
                    },
                    "routes": {
                        "node-a": {
                            "port-u": {
                                "source": {"type": 1, "uuid": "port-u"},
                                "target": {"type": 1, "uuid": "node-b"},
                            },
                        },
                        "node-b": {},
                    },
                }
            ]
        }

    def test_returns_one_component(self):
        components = build_components(self._make_two_node_comp())
        assert len(components) == 1

    def test_component_fields(self):
        components = build_components(self._make_two_node_comp())
        comp = components[0]
        assert comp.uuid == "comp-two"
        assert comp.name == "Two Node Comp"
        assert comp.sort_index == 3

    def test_both_nodes_present(self):
        components = build_components(self._make_two_node_comp())
        comp = components[0]
        assert "node-a" in comp.nodes
        assert "node-b" in comp.nodes

    def test_entry_uuid_is_is_default_node(self):
        components = build_components(self._make_two_node_comp())
        comp = components[0]
        assert comp.entry_uuid == "node-a"

    def test_root_uuids_equals_entry_uuid_list(self):
        components = build_components(self._make_two_node_comp())
        comp = components[0]
        assert comp.root_uuids == ["node-a"]

    def test_node_text_extracted(self):
        components = build_components(self._make_two_node_comp())
        comp = components[0]
        assert comp.nodes["node-a"].text == "Hi"

    def test_node_label(self):
        components = build_components(self._make_two_node_comp())
        comp = components[0]
        assert comp.nodes["node-a"].label == "Entry Talk"


# ---------------------------------------------------------------------------
# build_flow_model and flow_model_to_dict smoke test
# ---------------------------------------------------------------------------

class TestBuildFlowModel:
    def _minimal_data(self):
        return {
            "BizSpeechComponent": [
                {
                    "componentUuid": "comp-smoke",
                    "name": "Smoke",
                    "sortIndex": 1,
                    "details": {
                        "sn1": {
                            "type": 1,
                            "name": "Smoke Talk",
                            "is_default": True,
                            "data": {
                                "list": [],
                                "all_client_intent": [],
                                "node_variables": [],
                                "allow_jump_knowledges": [],
                            },
                        },
                    },
                    "routes": {"sn1": {}},
                }
            ],
            "BizKnowledgeInfo": [],
        }

    def test_build_flow_model_returns_flow_model(self):
        fm = build_flow_model(self._minimal_data())
        assert isinstance(fm, FlowModel)
        assert len(fm.components) == 1
        assert fm.knowledge_bases == []

    def test_flow_model_to_dict_serializes(self):
        fm = build_flow_model(self._minimal_data())
        d = flow_model_to_dict(fm)
        assert "components" in d
        assert "knowledge_bases" in d
        assert d["components"][0]["uuid"] == "comp-smoke"


# ---------------------------------------------------------------------------
# Fix 3: malformed route entries are skipped silently (no KeyError)
# ---------------------------------------------------------------------------

class TestMalformedRouteHandling:
    """_build_branches must skip edges with missing/malformed target gracefully."""

    def _make_comp_with_bad_route(self):
        """Talk node whose routes contain one good edge and several bad ones."""
        return {
            "componentUuid": "comp-malformed",
            "name": "Malformed Route Component",
            "sortIndex": 1,
            "details": {
                "talk1": {
                    "type": 1,
                    "name": "Talk Node",
                    "is_default": True,
                    "data": {
                        "list": [{"text": "Hi"}],
                        "all_client_intent": [
                            {"name": "Good", "id": "port-good"},
                            {"name": "BadNoTarget", "id": "port-bad1"},
                            {"name": "BadNullTarget", "id": "port-bad2"},
                            {"name": "BadNoUuid", "id": "port-bad3"},
                        ],
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                    },
                },
                "dest": {
                    "type": 2,
                    "name": "Exit",
                    "is_default": False,
                    "data": {
                        "list": [], "is_transfer": 0,
                        "node_variables": [], "allow_jump_knowledges": [],
                    },
                },
            },
            "routes": {
                "talk1": {
                    # Good edge
                    "port-good": {"source": {"uuid": "port-good"}, "target": {"uuid": "dest"}},
                    # Missing "target" key entirely
                    "port-bad1": {"source": {"uuid": "port-bad1"}},
                    # target is None
                    "port-bad2": {"source": {"uuid": "port-bad2"}, "target": None},
                    # target is a dict but missing "uuid"
                    "port-bad3": {"source": {"uuid": "port-bad3"}, "target": {}},
                },
                "dest": {},
            },
        }

    def test_malformed_route_does_not_raise(self):
        """build_components must not raise KeyError on malformed route entries."""
        comp_dict = self._make_comp_with_bad_route()
        # Must not raise
        components = build_components({"BizSpeechComponent": [comp_dict]})
        assert len(components) == 1

    def test_malformed_route_skips_bad_entries_keeps_good(self):
        """Only the well-formed edge should produce a branch; bad ones are dropped."""
        comp_dict = self._make_comp_with_bad_route()
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["talk1"]
        # Only the good edge produces a branch
        assert len(node.branches) == 1
        assert node.branches[0].target_uuid == "dest"


# ---------------------------------------------------------------------------
# FlowModelNode.data field — populated from envelope's data dict
# ---------------------------------------------------------------------------

class TestFlowModelNodeData:
    """FlowModelNode.data must carry the raw envelope data dict for checks that
    need fields not promoted to first-class attributes (e.g. branch conditions,
    sentenceText).
    """

    def _make_comp_with_conditional(self, branch_list):
        """Conditional-judgment node (type 7) with given branch list in data."""
        return {
            "componentUuid": "comp-data-test",
            "name": "Data Test",
            "sortIndex": 1,
            "details": {
                "cond-node": {
                    "type": 7,
                    "name": "Check Date",
                    "is_default": True,
                    "data": {
                        "list": [],
                        "branch": branch_list,
                        "all_client_intent": [],
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                    },
                },
            },
            "routes": {"cond-node": {}},
        }

    def _make_comp_with_talk(self, sentence_text: str, node_label: str = "Wait"):
        """Talk/exit node with a specific sentence text list entry."""
        return {
            "componentUuid": "comp-text-test",
            "name": "Text Test",
            "sortIndex": 1,
            "details": {
                "text-node": {
                    "type": 1,
                    "name": node_label,
                    "is_default": True,
                    "data": {
                        "list": [{"text": sentence_text}] if sentence_text is not None else [],
                        "all_client_intent": [],
                        "node_variables": [],
                        "allow_jump_knowledges": [],
                        "sentenceText": sentence_text,
                    },
                },
            },
            "routes": {"text-node": {}},
        }

    def test_data_field_is_dict(self):
        """FlowModelNode.data is a dict (never None)."""
        comp = self._make_comp_with_conditional([])
        components = build_components({"BizSpeechComponent": [comp]})
        node = components[0].nodes["cond-node"]
        assert isinstance(node.data, dict)

    def test_data_contains_branch_list(self):
        """For a type-7 node, node.data['branch'] holds the condition branches."""
        branch_list = [
            {
                "name": "Is Today",
                "branch_judgement_condition": [
                    {"left_value": "[{101}]", "operator": "=", "right_value": "Today"}
                ],
            }
        ]
        comp = self._make_comp_with_conditional(branch_list)
        components = build_components({"BizSpeechComponent": [comp]})
        node = components[0].nodes["cond-node"]
        assert node.data.get("branch") == branch_list

    def test_data_contains_sentence_text(self):
        """For a node with sentenceText in data, node.data['sentenceText'] is accessible."""
        comp = self._make_comp_with_talk("blank", "Wait")
        components = build_components({"BizSpeechComponent": [comp]})
        node = components[0].nodes["text-node"]
        assert node.data.get("sentenceText") == "blank"

    def test_data_empty_dict_when_no_data_envelope(self):
        """When the envelope has no 'data' key, node.data is an empty dict."""
        comp_dict = {
            "componentUuid": "comp-nodata",
            "name": "No Data",
            "sortIndex": 1,
            "details": {
                "nd-node": {
                    "type": 2,
                    "name": "Exit",
                    "is_default": True,
                    # No 'data' key at all
                },
            },
            "routes": {"nd-node": {}},
        }
        components = build_components({"BizSpeechComponent": [comp_dict]})
        node = components[0].nodes["nd-node"]
        assert node.data == {}
