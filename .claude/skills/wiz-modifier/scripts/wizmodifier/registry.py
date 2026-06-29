"""Registry mapping op names to their implementation callables.

Every op has the signature: op(bundle, params, minter) -> None.
"""

from __future__ import annotations

from collections.abc import Callable

from wizmodifier.ops import content, generic, identity, kb_edit, mutate, structure

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
    "rename-kb": kb_edit.rename_kb,
    "set-kb-intents": kb_edit.set_kb_intents,
    "add-kb-answer": kb_edit.add_kb_answer,
    "edit-kb-answer": kb_edit.edit_kb_answer,
    "remove-kb-answer": kb_edit.remove_kb_answer,
    "rewire-edge": mutate.rewire_edge,
    "delete-edge": mutate.delete_edge,
    "delete-node": mutate.delete_node,
    "rename-node": mutate.rename_node,
    "move-node": mutate.move_node,
    "complete-component": mutate.complete_component,
    "set-path": generic.set_path,
    "delete-path": generic.delete_path,
}


def get_op(name: str) -> Callable:
    if name not in OP_REGISTRY:
        raise ValueError(
            f"unknown op {name!r}; known ops: {', '.join(sorted(OP_REGISTRY))}"
        )
    return OP_REGISTRY[name]
