"""Tag authoring: build the SpeechTag vocabulary + emit SpeechTag/kbTag."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from wizbuilder.errors import CompileError
from wizbuilder.ids import IdMinter
from wizbuilder.manifest import Manifest

_TAG_TS = 1700000000000


@dataclass(frozen=True)
class TagCat:
    id: int
    is_mutex: int
    type: int
    values: dict[str, int]  # value label -> value id


@dataclass(frozen=True)
class TagVocabulary:
    ent_id: int | str
    categories: dict[str, TagCat]


def build_tag_vocabulary(manifest: Manifest, minter: IdMinter) -> TagVocabulary:
    ent_id = manifest.enterprise_id if manifest.enterprise_id is not None \
        else minter.int_id("enterprise")
    categories: dict[str, TagCat] = {}
    for spec in manifest.tags:
        values = {v: minter.int_id(f"tagval:{spec.name}:{v}") for v in spec.values}
        categories[spec.name] = TagCat(
            id=minter.int_id(f"tag:{spec.name}"),
            is_mutex=1 if spec.is_mutex else 0,
            type=spec.type,
            values=values,
        )
    # validate node assignments resolve
    for canvas in manifest.canvases:
        for node in canvas.nodes:
            for a in node.tags:
                cat = categories.get(a.category)
                if cat is None:
                    raise CompileError(
                        f"node {node.id!r} assigns unknown tag category {a.category!r}")
                for v in a.values:
                    if v not in cat.values:
                        raise CompileError(
                            f"node {node.id!r} assigns unknown tag value {v!r} "
                            f"in category {a.category!r}")
    return TagVocabulary(ent_id=ent_id, categories=categories)


def _category_dict(name: str, cat: TagCat, ent_id: int | str) -> dict[str, Any]:
    return {
        "id": cat.id,
        "name": name,
        "isMutex": cat.is_mutex,
        "type": cat.type,
        "tagProperty": 0,
        "entId": ent_id,
        "createTime": _TAG_TS,
        "modifyTime": _TAG_TS,
        "bizTagPropertyDTOS": [
            {"id": vid, "tagId": cat.id, "value": label}
            for label, vid in cat.values.items()
        ],
    }


def apply_tags(
    template: dict[str, Any], manifest: Manifest, vocabulary: TagVocabulary, minter: IdMinter
) -> dict[str, Any]:
    if not manifest.tags:
        return template
    # SpeechTag: all declared categories + all values (name order preserved)
    speech_tag = [
        _category_dict(spec.name, vocabulary.categories[spec.name], vocabulary.ent_id)
        for spec in manifest.tags
    ]
    template["SpeechTag"] = json.dumps(speech_tag, ensure_ascii=False, separators=(",", ":"))
    # kbTag: sorted unique category ids any node assigns
    assigned: set[int] = set()
    for canvas in manifest.canvases:
        for node in canvas.nodes:
            for a in node.tags:
                assigned.add(vocabulary.categories[a.category].id)
    template["kbTag"] = sorted(assigned)
    return template
