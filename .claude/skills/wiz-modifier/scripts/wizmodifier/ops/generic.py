"""Generic escape-hatch ops: set/delete an arbitrary path in a top-level field."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.io import InputBundle


def _descend(node, step):
    """Move one level into node by step, raising a clear ValueError on misuse."""
    if isinstance(node, dict):
        return node[step]  # caller guarantees presence
    if isinstance(node, list):
        if not isinstance(step, int):
            raise ValueError(f"cannot index a list with non-int key {step!r}")
        if step < 0 or step >= len(node):
            raise ValueError(f"list index {step} out of range (length {len(node)})")
        return node[step]
    raise ValueError(f"cannot descend into {type(node).__name__} at {step!r}")


def _navigate(root, pointer: list, create: bool):
    """Walk pointer[:-1], returning (container, last_key). Pointer must be non-empty."""
    if not pointer:
        raise ValueError("pointer must not be empty")
    node = root
    for step in pointer[:-1]:
        if isinstance(node, dict) and step not in node:
            if not create:
                raise ValueError(
                    f"path segment {step!r} does not exist (use create: true to add)"
                )
            node[step] = {}
        node = _descend(node, step)
    return node, pointer[-1]


def set_path(bundle: InputBundle, params: dict, minter) -> None:
    key = params["key"]
    pointer = params["pointer"]
    value = params["value"]
    create = params.get("create", False)
    root = codec.decode(bundle.data[key])
    container, last = _navigate(root, pointer, create)
    if isinstance(container, dict):
        if last not in container and not create:
            raise ValueError(f"key {last!r} does not exist (use create: true to add)")
        container[last] = value
    elif isinstance(container, list):
        if not isinstance(last, int) or last < 0 or last >= len(container):
            raise ValueError(f"list index {last!r} out of range (length {len(container)})")
        container[last] = value
    else:
        raise ValueError(f"cannot set into {type(container).__name__}")
    bundle.data[key] = codec.encode(root)


def delete_path(bundle: InputBundle, params: dict, minter) -> None:
    key = params["key"]
    pointer = params["pointer"]
    root = codec.decode(bundle.data[key])
    container, last = _navigate(root, pointer, create=False)
    if isinstance(container, dict):
        if last not in container:
            raise ValueError(f"key {last!r} does not exist")
        del container[last]
    elif isinstance(container, list):
        if not isinstance(last, int) or last < 0 or last >= len(container):
            raise ValueError(f"list index {last!r} out of range (length {len(container)})")
        del container[last]
    else:
        raise ValueError(f"cannot delete from {type(container).__name__}")
    bundle.data[key] = codec.encode(root)
