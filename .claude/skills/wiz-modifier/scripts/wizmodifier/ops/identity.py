"""Identity ops: speechId, componentUuid, BSC name, BSC id."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, require_component, set_components


def _resolve_speech_id(value, minter) -> int:
    if value == "random":
        return minter.random_speech_id()
    if isinstance(value, int):
        return value
    raise ValueError(f"set-speech-id: value must be an int or 'random', got {value!r}")


def set_speech_id(bundle: InputBundle, params: dict, minter) -> None:
    """Propagate a new speechId to every top-level field that carries one.

    Mirrors wiz-builder's generic walk (identity.py) so populated and empty
    fields both get the new id.
    """
    speech_id = _resolve_speech_id(params.get("value", "random"), minter)
    for key, raw in bundle.data.items():
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            decoded = codec.decode(raw)
        except (ValueError, TypeError):
            continue
        changed = False
        if isinstance(decoded, list):
            for item in decoded:
                if isinstance(item, dict) and "speechId" in item:
                    item["speechId"] = speech_id
                    changed = True
        elif isinstance(decoded, dict) and "speechId" in decoded:
            decoded["speechId"] = speech_id
            changed = True
        if changed:
            bundle.data[key] = codec.encode(decoded)


def set_component_uuid(bundle: InputBundle, params: dict, minter) -> None:
    """Set a component's componentUuid to an explicit value or a minted one.

    "random" mints a deterministic, manifest-hash-seeded UUID (new relative to
    the original file but reproducible across runs, matching wiz-builder).
    """
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    value = params.get("value", "random")
    if value == "random":
        value = str(minter.uuid(f"modifier-uuid:{params['component']}"))
    comp["componentUuid"] = value
    set_components(bundle, comps)


def set_bsc_name(bundle: InputBundle, params: dict, minter) -> None:
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    comp["name"] = params["value"]
    set_components(bundle, comps)


def set_bsc_id(bundle: InputBundle, params: dict, minter) -> None:
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    comp["id"] = params["value"]
    set_components(bundle, comps)
