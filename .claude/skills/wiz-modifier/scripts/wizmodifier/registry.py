"""Registry mapping op names to their implementation callables.

Every op has the signature: op(bundle, params, minter) -> None.
"""

from __future__ import annotations

from collections.abc import Callable

from wizmodifier.ops import (
    content,
    generic,
    identity,
    intents_xlsx,
    kb_edit,
    kb_xlsx,
    mutate,
    structure,
    tags,
)

OP_REGISTRY: dict[str, Callable] = {
    "set-speech-id": identity.set_speech_id,
    "set-component-uuid": identity.set_component_uuid,
    "set-bsc-name": identity.set_bsc_name,
    "set-bsc-id": identity.set_bsc_id,
    "add-bsc-keys": structure.add_bsc_keys,
    "populate-details": structure.populate_details,
    "add-component": structure.add_component,
    "append-node": structure.append_node,
    "add-variable": content.add_variable,
    "add-intent": content.add_intent,
    "add-kb": content.add_kb,
    "set-hotwords": content.set_hotwords,
    "set-intent-training": content.set_intent_training,
    "import-intents-xlsx": intents_xlsx.import_intents_xlsx,
    "import-kb-xlsx": kb_xlsx.import_kb_xlsx,
    "rename-kb": kb_edit.rename_kb,
    "set-kb-intents": kb_edit.set_kb_intents,
    "add-kb-answer": kb_edit.add_kb_answer,
    "edit-kb-answer": kb_edit.edit_kb_answer,
    "remove-kb-answer": kb_edit.remove_kb_answer,
    "set-kb-multiround": kb_edit.set_kb_multiround,
    "delete-kb": kb_edit.delete_kb,
    "rewire-edge": mutate.rewire_edge,
    "delete-edge": mutate.delete_edge,
    "delete-node": mutate.delete_node,
    "rename-node": mutate.rename_node,
    "move-node": mutate.move_node,
    "complete-component": mutate.complete_component,
    "set-node-config": mutate.set_node_config,
    "set-node-tags": tags.set_node_tags,
    "set-path": generic.set_path,
    "delete-path": generic.delete_path,
}


def get_op(name: str) -> Callable:
    if name not in OP_REGISTRY:
        raise ValueError(
            f"unknown op {name!r}; known ops: {', '.join(sorted(OP_REGISTRY))}"
        )
    return OP_REGISTRY[name]
