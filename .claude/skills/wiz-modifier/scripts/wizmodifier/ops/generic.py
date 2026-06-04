"""Generic escape-hatch ops: set/delete an arbitrary path in a top-level field."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.io import InputBundle


def _navigate(root, pointer: list, create: bool):
    """Walk pointer[:-1], returning (container, last_key)."""
    node = root
    for step in pointer[:-1]:
        if isinstance(node, dict):
            if step not in node:
                if not create:
                    raise ValueError(
                        f"path segment {step!r} does not exist (use create: true to add)"
                    )
                node[step] = {}
            node = node[step]
        elif isinstance(node, list):
            node = node[step]
        else:
            raise ValueError(f"cannot descend into {type(node).__name__} at {step!r}")
    return node, pointer[-1]


def set_path(bundle: InputBundle, params: dict, minter) -> None:
    key = params["key"]
    pointer = params["pointer"]
    create = params.get("create", False)
    root = codec.decode(bundle.data[key])
    container, last = _navigate(root, pointer, create)
    if isinstance(container, dict):
        if last not in container and not create:
            raise ValueError(f"key {last!r} does not exist (use create: true to add)")
        container[last] = params["value"]
    elif isinstance(container, list):
        container[last] = params["value"]
    else:
        raise ValueError(f"cannot set into {type(container).__name__}")
    bundle.data[key] = codec.encode(root)


def delete_path(bundle: InputBundle, params: dict, minter) -> None:
    key = params["key"]
    pointer = params["pointer"]
    root = codec.decode(bundle.data[key])
    container, last = _navigate(root, pointer, create=False)
    del container[last]
    bundle.data[key] = codec.encode(root)
