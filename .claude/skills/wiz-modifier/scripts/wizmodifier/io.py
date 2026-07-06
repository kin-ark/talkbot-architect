"""Load a WIZ export (bare JSON or ZIP) into an InputBundle; package output."""

from __future__ import annotations

import copy
import json
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from wizmodifier import codec

_SKILL_DIR = Path(__file__).resolve().parents[2]
_WC_SCRIPTS = _SKILL_DIR.parent / "wiz-checker" / "scripts"
if str(_WC_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WC_SCRIPTS))

from wizcheck.component_adapter import (  # noqa: E402
    component_export_to_full,
    full_to_component_export,
    is_component_export,
)


@dataclass
class InputBundle:
    """The decoded contents of a WIZ export plus its WAV inventory.

    data:            top-level dict (values are still JSON-encoded strings)
    speech_name:     the speech*.json filename to use on output
    wavs:            mapping of wav filename -> raw bytes (empty for bare JSON)
    is_component:    True if the input is a component-export envelope
    component_source: deep copy of the original component envelope (None for full exports)
    """

    data: dict
    speech_name: str
    wavs: dict[str, bytes] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    is_component: bool = False
    component_source: dict | None = None

    @classmethod
    def load(cls, path: Path) -> InputBundle:
        path = Path(path)
        if path.suffix.lower() == ".zip":
            return cls._load_zip(path)
        text = path.read_text(encoding="utf-8")
        raw = json.loads(text)
        if is_component_export(raw):
            data = component_export_to_full(raw)
            # Encode decoded lists to JSON strings to match full-export shape ops expect
            data["BizSpeechComponent"] = codec.encode(data.get("BizSpeechComponent", []))
            data["SentenceCutSpeech"] = codec.encode(data.get("SentenceCutSpeech", []))
            data["SpeechIntent"] = codec.encode(data.get("SpeechIntent", []))
            data["SpeechVariable"] = codec.encode(data.get("SpeechVariable", []))
            data["SpeechAudio"] = codec.encode(data.get("SpeechAudio", []))
            return cls(
                data=data,
                speech_name=path.name,
                is_component=True,
                component_source=copy.deepcopy(raw),
            )
        return cls(data=raw, speech_name=path.name)

    @classmethod
    def _load_zip(cls, path: Path) -> InputBundle:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            speech = [n for n in names if Path(n).name.startswith("speech") and n.endswith(".json")]
            if len(speech) != 1:
                raise ValueError(
                    f"expected exactly one speech*.json in {path.name}, found {speech}"
                )
            speech_name = Path(speech[0]).name
            data = json.loads(z.read(speech[0]).decode("utf-8"))
            wavs = {
                Path(n).name: z.read(n)
                for n in names
                if n.lower().endswith(".wav")
            }
        return cls(data=data, speech_name=speech_name, wavs=wavs)

    def serialize_json(self) -> str:
        """Top-level dict re-serialized with compact separators (key order preserved)."""
        return codec.encode(self.data)


def write_output(bundle: InputBundle, out_path: Path, fmt: str) -> None:
    """Write the bundle to out_path in the requested format.

    fmt is one of: "json", "zip", "zip-no-wav".
    ZIP entries are flat at the root (matching real WIZ exports). WAV bytes
    pass through unmodified.

    For component-export inputs, output is JSON only; ZIP requests raise ValueError.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if bundle.is_component:
        if fmt != "json":
            raise ValueError("component-export output is JSON only")
        src = bundle.component_source or {}
        name = src.get("name")
        envelope = full_to_component_export(bundle.data, name=name, base=src)
        out_path.write_text(codec.encode(envelope), encoding="utf-8")
        return

    payload = bundle.serialize_json()
    if fmt == "json":
        out_path.write_text(payload, encoding="utf-8")
        return

    if fmt not in ("zip", "zip-no-wav"):
        raise ValueError(f"unknown output format: {fmt!r}")

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(bundle.speech_name, payload.encode("utf-8"))
        if fmt == "zip":
            for name, data in bundle.wavs.items():
                z.writestr(name, data)
