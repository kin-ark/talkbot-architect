"""Build downloadable export payloads for the /export endpoints.

Each function returns ``(content, media_type, filename)`` — no FastAPI here, so
the route handlers stay thin. Extracted from main.py.
"""
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path

import speechname
from wizmodifier.io import InputBundle, write_output


def export_full(s) -> tuple[bytes | str, str, str]:
    """GET /export — the whole dialogue (component DTO / audio ZIP / plain JSON)."""
    if s.is_component:
        from wizcheck.component_adapter import full_to_component_export
        nm = speechname.read_speech_name(s.current())
        dto = full_to_component_export(s.current(), base=s.component_base, name=nm)
        body = json.dumps(dto, ensure_ascii=False, indent=2).encode("utf-8")
        stem = speechname.slugify_filename(nm).removesuffix(".json") if nm else "component"
        return body, "application/json", f"{stem}.component.json"

    data = s.current()
    nm = speechname.read_speech_name(data)
    base = speechname.slugify_filename(nm).removesuffix(".json") if nm else "speech_export"
    # Internal entry MUST be a speech*.json (WIZ + InputBundle.load require it);
    # the slugged <base> is only the download filename, never the zip entry.
    sn = s.speech_name if (s.speech_name.startswith("speech")
                           and s.speech_name.endswith(".json")) else "speech_export.json"

    if s.wavs:  # has audio → import-ready ZIP via the engine writer
        bundle = InputBundle(data=data, speech_name=sn, wavs=s.wavs)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            write_output(bundle, tmp_path, fmt="zip")
            payload = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)
        return payload, "application/zip", f"{base}.zip"

    # no audio → JSON
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return payload, "application/json", f"{base}.json"


def export_single_component(data: dict, uuid: str) -> tuple[bytes, str, str]:
    """GET /export/component?uuid=… — one component as a DTO. Raises KeyError if
    the uuid is unknown (caller maps to 404)."""
    import agents
    dto = agents.export_component_dto(data, uuid)   # raises KeyError on unknown uuid
    raw = data.get("BizSpeechComponent")
    comps = json.loads(raw) if isinstance(raw, str) else (raw or [])
    nm = next((c.get("name") for c in comps if isinstance(c, dict)
               and c.get("componentUuid") == uuid), None) or "component"
    stem = speechname.slugify_filename(nm).removesuffix(".json") or "component"
    body = json.dumps(dto, ensure_ascii=False, indent=2).encode("utf-8")
    return body, "application/json", f"{stem}.component.json"


def export_components_zip(data: dict) -> tuple[bytes, str, str]:
    """GET /export/component (no uuid) — a ZIP of the split components +
    intent/KB Excel sheets."""
    from wizcheck.component_adapter import full_to_component_export
    from wizmodifier.ops.intents_xlsx import intent_export_rows
    from wizmodifier.ops.kb_xlsx import kb_export_rows
    from wizmodifier.xlsx import write_sheet

    nm = speechname.read_speech_name(data) or "component"
    stem = speechname.slugify_filename(nm).removesuffix(".json") or "component"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        raw_comps = data.get("BizSpeechComponent")
        comps = json.loads(raw_comps) if isinstance(raw_comps, str) else (raw_comps or [])
        main_comps = [c for c in comps if isinstance(c, dict) and c.get("category") in (1, None)]
        if main_comps:
            main_data = data.copy()
            main_data["BizSpeechComponent"] = main_comps
            main_dto = full_to_component_export(main_data, name=nm, category=1)
            zf.writestr(f"{stem}.component.json",
                        json.dumps(main_dto, ensure_ascii=False, indent=2).encode("utf-8"))

        mr_comps = [c for c in comps if isinstance(c, dict) and c.get("category") == 2]
        if mr_comps:
            mr_data = data.copy()
            mr_data["BizSpeechComponent"] = mr_comps
            mr_dto = full_to_component_export(mr_data, name=nm, category=2)
            zf.writestr(f"{stem} (multi-round).component.json",
                        json.dumps(mr_dto, ensure_ascii=False, indent=2).encode("utf-8"))

        _si = data.get("SpeechIntent", "[]")
        si = json.loads(_si) if isinstance(_si, str) else (_si or [])
        intent_rows = intent_export_rows(si)
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
            tmp_intent = Path(tmp.name)
        try:
            write_sheet(tmp_intent, ["Intent", "Type", "Content", "Language"], intent_rows,
                        note="Note:\n1,Intent column is the intent name;\n2,Type is Keyword or User response;\n3,Content per type")
            zf.write(tmp_intent, f"{stem} intents.xls")
        finally:
            tmp_intent.unlink(missing_ok=True)

        _bk = data.get("BizKnowledgeInfo", "[]")
        bk = json.loads(_bk) if isinstance(_bk, str) else (_bk or [])
        kb_rows = kb_export_rows(bk, si)
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
            tmp_kb = Path(tmp.name)
        try:
            write_sheet(tmp_kb, ["Title", "Intent", "Dialogue Content"], kb_rows,
                        note="Note:\nTitle = KB name; Intent = trigger intent; Dialogue Content = answer")
            zf.write(tmp_kb, f"{stem} KB.xls")
        finally:
            tmp_kb.unlink(missing_ok=True)

    return buf.getvalue(), "application/zip", f"{stem}.components.zip"
