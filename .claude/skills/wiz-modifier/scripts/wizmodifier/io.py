"""Load a WIZ export (bare JSON or ZIP) into an InputBundle; package output."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from wizmodifier import codec


@dataclass
class InputBundle:
    """The decoded contents of a WIZ export plus its WAV inventory.

    data:        top-level dict (values are still JSON-encoded strings)
    speech_name: the speech*.json filename to use on output
    wavs:        mapping of wav filename -> raw bytes (empty for bare JSON)
    """

    data: dict
    speech_name: str
    wavs: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "InputBundle":
        path = Path(path)
        if path.suffix.lower() == ".zip":
            return cls._load_zip(path)
        text = path.read_text(encoding="utf-8")
        return cls(data=json.loads(text), speech_name=path.name)

    @classmethod
    def _load_zip(cls, path: Path) -> "InputBundle":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            speech = [n for n in names if Path(n).name.startswith("speech") and n.endswith(".json")]
            if len(speech) != 1:
                raise IOError(
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
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
