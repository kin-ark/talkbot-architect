from __future__ import annotations

# Load .env before anything reads os.environ — python-dotenv no-ops when
# no .env is present, so this is safe in production too.
from dotenv import load_dotenv
load_dotenv()

import json  # noqa: E402
import time  # noqa: E402
import queue  # noqa: E402
import threading  # noqa: E402
import os  # noqa: E402
import ipaddress  # noqa: E402
import hmac  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from urllib.parse import urlparse  # noqa: E402
import tempfile  # noqa: E402
import io  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402

from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.requests import Request  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import agents  # noqa: E402
import backup  # noqa: E402
import config_store  # noqa: E402
import models_catalog  # noqa: E402
import samples  # noqa: E402
import speechname  # noqa: E402
from auth import PasswordGateMiddleware  # noqa: E402
from config_store import any_override, effective_key_set  # noqa: E402
from identity import ClientCookieMiddleware, client_id  # noqa: E402
from llm.base import LLMClient  # noqa: E402
from llm.factory import LLMConfigError, make_client  # noqa: E402
from orchestrator import run_turn, run_turn_stream  # noqa: E402
from registry import REGISTRY  # noqa: E402
from session import Session  # noqa: E402
from session_store import SessionStore  # noqa: E402
from wizmodifier.io import InputBundle, write_output  # noqa: E402
from wizcheck.component_adapter import is_component_export, component_export_to_full  # noqa: E402

from logging_setup import configure_logging, log, RequestLogMiddleware  # noqa: E402
configure_logging()  # noqa: E402

try:
    backup.start_scheduler()
except Exception as e:  # pragma: no cover
    log.error("", extra={"ev": "backup_error", "err": f"scheduler start: {e}"}, exc_info=e)

_THINKING_BUDGET = 2048
# SSE keepalive interval. A turn can be silent for a long stretch (slow gateway
# first token, or a long-running tool like build->checker). Reverse proxies in
# front of the dashboard (e.g. Cloudflare Tunnel) drop a connection that sends
# no bytes within ~100s -> the client sees "stream failed: 524". We emit an SSE
# comment every HEARTBEAT_S so the connection never goes idle. Comments (": ...")
# are ignored by the frontend parser, which only acts on "data: " lines.
_HEARTBEAT_S = 15
_ATTACH_MAX_BYTES = 5 * 1024 * 1024
# Cap the /session upload and the /chat message so a huge body can't OOM the
# process. Env-overridable.
_MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
_MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "100000"))
_STARTED = time.time()

_IMAGE_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",   # RIFF....WEBP; good enough with the ext check below
}
_IMAGE_EXTS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".gif": "image/gif", ".webp": "image/webp"}
_MAX_IMAGES = 4

app = FastAPI(title="Talkbot Architect API")
# With allow_credentials=True a wildcard origin is invalid, so we list origins.
# Prod sets CORS_ORIGINS explicitly (or serves the SPA same-origin → CORS unused).
# When unset, default to the Vite dev server so local dev (5173 → 8000) works
# out of the box now that the frontend sends credentials.
_DEFAULT_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
_cors_origins = (
    [o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip()]
    if os.environ.get("CORS_ORIGINS")
    else _DEFAULT_DEV_ORIGINS
)
app.add_middleware(
    CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.add_middleware(PasswordGateMiddleware)
app.add_middleware(ClientCookieMiddleware)
app.add_middleware(RequestLogMiddleware)


def _error_body(exc: Exception) -> dict:
    return {"error": {"type": type(exc).__name__, "message": str(exc)}}


class LLMProviderError(Exception):
    """Wraps an upstream LLM/provider failure so the handler can return 502."""


@app.exception_handler(LLMProviderError)
async def _provider_error(request: Request, exc: LLMProviderError):
    log.error("", extra={"ev": "exc", "path": request.url.path, "err": f"{type(exc).__name__}: {exc}"}, exc_info=exc)
    return JSONResponse(status_code=502, content=_error_body(exc))


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.error("", extra={"ev": "exc", "path": request.url.path, "err": f"{type(exc).__name__}: {exc}"}, exc_info=exc)
    return JSONResponse(status_code=500, content=_error_body(exc))


# ---------------------------------------------------------------------------
# Per-client dependencies
# ---------------------------------------------------------------------------

def current_store(cid: str = Depends(client_id)) -> SessionStore:
    return REGISTRY.store(cid)


def current_session(store: SessionStore = Depends(current_store)) -> Session:
    return store.active()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(max_length=_MAX_MESSAGE_CHARS)


class ConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    show_reasoning: Optional[bool] = None
    model_id: Optional[str] = None
    custom_vision: Optional[bool] = None


class RenameRequest(BaseModel):
    name: str


class BotNameRequest(BaseModel):
    name: str


class NodeTextRequest(BaseModel):
    label: Optional[str] = None
    prompt: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers / dependencies
# ---------------------------------------------------------------------------

def _image_media_type(name: str, raw: bytes) -> str | None:
    """Return an image media_type if the bytes/name look like a supported image, else None."""
    for magic, mt in _IMAGE_MAGIC.items():
        if raw.startswith(magic):
            if mt == "image/webp" and b"WEBP" not in raw[:16]:
                continue
            return mt
    ext = Path(name).suffix.lower()
    return _IMAGE_EXTS.get(ext)


def _require_session(s: Session = Depends(current_session)) -> Session:
    """Raise 503 if no data has been loaded into the active session yet."""
    if not s._stack:
        raise HTTPException(status_code=503, detail="no session loaded")
    return s


@contextmanager
def _exclusive(s: Session):
    """Hold the session lock for a swap/reset (load/new/activate). Non-blocking:
    if a chat turn already holds it, refuse with 409 rather than mutate the
    session out from under the running turn (or block the event loop)."""
    if not s._lock.acquire(blocking=False):
        raise HTTPException(status_code=409,
                            detail="a chat turn is in progress; try again in a moment")
    try:
        yield
    finally:
        s._lock.release()


def _classify_attachment(name: str, path: str) -> tuple[str, str | None]:
    """Return (kind, excerpt). kind: intent-xlsx | kb-xlsx | read."""
    lower = name.lower()
    if lower.endswith((".xls", ".xlsx")):
        try:
            from wizmodifier.xlsx import read_rows
            rows = read_rows(path)
        except Exception:
            return "read", "(unreadable spreadsheet)"
        for row in rows[:5]:
            cells = {str(c).strip().lower() for c in row if c is not None}
            if {"intent", "type", "content"} <= cells:
                return "intent-xlsx", None
            if {"title", "intent", "dialogue content"} <= cells:
                return "kb-xlsx", None
        excerpt = "\n".join(
            " | ".join("" if c is None else str(c) for c in r) for r in rows[:40])
        return "read", excerpt[:8000]
    # text / json / other -> read
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "read", "(unreadable file)"
    return "read", text[:8000]


def _reconstruct_transcript(messages) -> list[dict]:
    """Backend LLM Messages -> frontend chat bubbles (plain text; tool turns dropped)."""
    out: list[dict] = []
    for m in messages:
        if m.role == "user" and m.content:
            out.append({"role": "user", "text": m.content})
        elif m.role == "assistant" and m.content:
            out.append({"role": "agent", "text": m.content})
    return out


def _component_index_of(data: dict, uuid: str) -> Optional[int]:
    """Return the BizSpeechComponent list index of the component whose
    decoded details contain *uuid*, or None if no component contains it."""
    comps = agents.unwrap(data.get("BizSpeechComponent")) or []
    for i, comp in enumerate(comps):
        details = agents.unwrap(comp.get("details"))
        if isinstance(details, dict) and uuid in details:
            return i
    return None


def _active_payload(s: Session) -> dict:
    """Return the rehydrate payload for the current active session.
    Conversational state (transcript/proposal/undo-redo/usage) is always
    returned, even when the doc stack is empty, so returning to a chatted-but-
    unbuilt session does not lose its chat."""
    base = {
        "id": s.id,
        "bot_name": None,
        "summary": None,
        "findings": [],
        "transcript": _reconstruct_transcript(s.transcript),
        "proposal": s.pending,
        "can_undo": s.can_undo(),
        "can_redo": s.can_redo(),
        "usage": s.usage,
        "is_component": s.is_component,
        "component_warnings": [],
    }
    if not s._stack:
        return base
    data = s.current()
    base.update({
        "bot_name": speechname.read_speech_name(data),
        "summary": s.summary(),
        "findings": s.findings(),
        "component_warnings": agents.component_export_warnings(data) if s.is_component else [],
    })
    return base


def _parse_or_400(content: bytes) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    try:
        agents.parse_dict(data)  # parse-only structural check; raises on a bad export
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Talkbot export: {e}")
    return data


def _resolve_model(cfg) -> tuple[str, str, str | None]:
    """Return (provider, model, base_url).

    Custom (model_id == CUSTOM_MODEL_ID): the user-typed provider/model + base_url.
    Otherwise: the picked catalog entry, with the user's base_url overriding the
    entry's default. The model is ALWAYS explicit — never the LLM_MODEL env
    default (the DeepSeek-got-Opus bug).
    """
    if cfg.model_id == models_catalog.CUSTOM_MODEL_ID:
        provider = cfg.provider or "anthropic"
        model = cfg.model
        entry_base = None
    else:
        entry = models_catalog.entry_by_id(cfg.model_id)
        if entry is None and cfg.model_id:
            raise LLMConfigError(
                f"configured model '{cfg.model_id}' is not in the catalog; "
                f"pick one in Settings")
        if entry is None:
            entry = models_catalog.entry_by_id(models_catalog.default_entry_id())
        provider, model, entry_base = entry.provider, entry.model, entry.base_url
    base_url = cfg.base_url or entry_base
    return provider, model, base_url


def _model_is_vision(cfg) -> bool:
    """Return True if the resolved model can process images."""
    if cfg.model_id == models_catalog.CUSTOM_MODEL_ID:
        return bool(cfg.custom_vision)
    entry = models_catalog.entry_by_id(cfg.model_id) or \
        models_catalog.entry_by_id(models_catalog.default_entry_id())
    return bool(getattr(entry, "vision", False))


def get_client(cid: str = Depends(client_id)) -> LLMClient:
    """Build an LLMClient from per-client config overrides + catalog."""
    cfg = config_store.config_for(cid)
    try:
        provider, model, base_url = _resolve_model(cfg)
    except LLMConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    api_key = cfg.api_key
    resolved = (provider or "anthropic").lower()
    thinking_budget = _THINKING_BUDGET if (cfg.show_reasoning and resolved == "anthropic") else None
    try:
        return make_client(provider=provider, api_key=api_key, model=model,
                           base_url=base_url, thinking_budget=thinking_budget)
    except LLMConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))


def _config_response(cfg) -> dict:
    """Build the /config response body. NEVER includes the api_key value."""
    try:
        provider, model, base_url = _resolve_model(cfg)
    except LLMConfigError:
        provider, model, base_url = None, None, None
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "model_id": cfg.model_id or models_catalog.default_entry_id(),
        "key_set": effective_key_set(provider, cfg),
        "source": "override" if any_override(cfg) else "env",
        "show_reasoning": cfg.show_reasoning,
        "custom_vision": cfg.custom_vision,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "live_sessions": len(REGISTRY._stores), "uptime_s": int(time.time() - _STARTED)}


def _require_admin(x_admin_token: str | None = Header(default=None)):
    """Gate the admin endpoints (they touch ALL tenants' data) behind a
    dedicated ADMIN_TOKEN. When ADMIN_TOKEN is unset the endpoints are disabled
    entirely (404) so they can't leak cross-tenant data on an open LAN deploy."""
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        raise HTTPException(status_code=404, detail="not found")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, token):
        raise HTTPException(status_code=403, detail="admin token required")


@app.get("/admin/backup")
async def admin_backup(_: None = Depends(_require_admin)):
    data, filename = backup.open_backup_stream()
    log.info("", extra={"ev": "backup", "kind": "download", "bytes": len(data)})
    return Response(content=data, media_type="application/gzip",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/admin/restore")
async def admin_restore(file: UploadFile = File(...), _: None = Depends(_require_admin)):
    raw = await file.read()
    try:
        result = backup.restore_from(io.BytesIO(raw))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"invalid backup: {e}")
    REGISTRY.reset()
    log.info("", extra={"ev": "restore", "safety": result["safety_backup"]})
    return result


@app.get("/config")
async def get_config(cid: str = Depends(client_id)):
    """Return current effective LLM config. api_key value is NEVER included."""
    return _config_response(config_store.config_for(cid))


# Cloud-metadata endpoints an SSRF would target. Private/VPN IPs are NOT
# blocked on purpose — the internal LLM gateway is a private address.
_BLOCKED_URL_HOSTS = {"169.254.169.254", "metadata.google.internal", "fd00:ec2::254"}


def _validate_base_url(url: str) -> None:
    """Reject a custom base_url that isn't http(s) or points at a cloud-metadata
    endpoint (SSRF guard). Raises HTTPException(400) on a bad value."""
    if not url:
        return
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="base_url must be http:// or https://")
    host = (p.hostname or "").lower()
    if not host:
        raise HTTPException(status_code=400, detail="base_url must include a host")
    if host in _BLOCKED_URL_HOSTS:
        raise HTTPException(status_code=400, detail="base_url host is not allowed")
    try:
        # 169.254.0.0/16 + fe80::/10 (link-local) covers the IMDS metadata range.
        if ipaddress.ip_address(host).is_link_local:
            raise HTTPException(status_code=400, detail="base_url host is not allowed")
    except ValueError:
        pass  # a hostname, not a literal IP — fine


@app.put("/config")
async def put_config(update: ConfigUpdate, cid: str = Depends(client_id)):
    """Override any subset of provider/model/base_url/api_key in memory.

    An empty-string api_key is treated as 'leave unchanged' (not a clear).
    Returns the same shape as GET /config.
    """
    cfg = config_store.config_for(cid)
    if update.provider is not None:
        cfg.provider = update.provider
    if update.model is not None:
        cfg.model = update.model
    if update.base_url is not None:
        _validate_base_url(update.base_url)
        cfg.base_url = update.base_url
    # Empty string means "leave unchanged"; only update when truthy
    if update.api_key:
        cfg.api_key = update.api_key
    if update.show_reasoning is not None:
        cfg.show_reasoning = update.show_reasoning
    if update.model_id is not None:
        cfg.model_id = update.model_id
    if update.custom_vision is not None:
        cfg.custom_vision = update.custom_vision
    return _config_response(cfg)


@app.post("/config/clear")
async def clear_config(cid: str = Depends(client_id)):
    """Reset all CONFIG overrides — effective config reverts to env vars."""
    cfg = config_store.config_for(cid)
    cfg.provider = cfg.model = cfg.base_url = cfg.api_key = None
    cfg.model_id = None
    cfg.show_reasoning = True
    cfg.custom_vision = False
    return _config_response(cfg)


@app.get("/models")
async def list_models():
    """List the curated model catalog for the Settings dropdown. No secrets."""
    cat = models_catalog.load_catalog()
    return {
        "models": [{"id": e.id, "label": e.label, "provider": e.provider,
                    "base_url": e.base_url, "group": e.group, "vision": e.vision} for e in cat],
        "default": models_catalog.default_entry_id(),
        "custom_id": models_catalog.CUSTOM_MODEL_ID,
        "providers": models_catalog.PROVIDERS,
    }


@app.get("/export")
async def export_current(s: Session = Depends(_require_session)):
    if s.is_component:
        from wizcheck.component_adapter import full_to_component_export
        nm = speechname.read_speech_name(s.current())
        dto = full_to_component_export(s.current(), base=s.component_base, name=nm)
        body = json.dumps(dto, ensure_ascii=False, indent=2).encode("utf-8")
        stem = speechname.slugify_filename(nm).removesuffix(".json") if nm else "component"
        return Response(content=body, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{stem}.component.json"'})

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
        return Response(
            content=payload,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{base}.zip"'},
        )

    # no audio → JSON (current behavior)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{base}.json"'},
    )


@app.get("/export/component")
async def export_component(uuid: str | None = None, s: Session = Depends(_require_session)):
    if s.is_component:
        raise HTTPException(status_code=400, detail="this session is already a component; use /export")
    data = s.current()

    # Single component export (uuid provided)
    if uuid is not None:
        try:
            dto = agents.export_component_dto(data, uuid)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown component")
        raw = data.get("BizSpeechComponent")
        comps = json.loads(raw) if isinstance(raw, str) else (raw or [])
        nm = next((c.get("name") for c in comps if isinstance(c, dict)
                   and c.get("componentUuid") == uuid), None) or "component"
        stem = speechname.slugify_filename(nm).removesuffix(".json") or "component"
        body = json.dumps(dto, ensure_ascii=False, indent=2).encode("utf-8")
        return Response(content=body, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{stem}.component.json"'})

    # Whole-dialog export: return a ZIP bundle with components + intent/KB Excel
    from wizcheck.component_adapter import full_to_component_export
    from wizmodifier.ops.intents_xlsx import intent_export_rows
    from wizmodifier.ops.kb_xlsx import kb_export_rows
    from wizmodifier.xlsx import write_sheet

    nm = speechname.read_speech_name(data) or "component"
    stem = speechname.slugify_filename(nm).removesuffix(".json") or "component"

    # Build the ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Main-flow components (category=1)
        raw_comps = data.get("BizSpeechComponent")
        comps = json.loads(raw_comps) if isinstance(raw_comps, str) else (raw_comps or [])
        main_comps = [c for c in comps if isinstance(c, dict) and c.get("category") in (1, None)]
        if main_comps:
            # Export only main-flow components
            main_data = data.copy()
            main_data["BizSpeechComponent"] = main_comps
            main_dto = full_to_component_export(main_data, name=nm, category=1)
            main_json = json.dumps(main_dto, ensure_ascii=False, indent=2).encode("utf-8")
            zf.writestr(f"{stem}.component.json", main_json)

        # Multi-round components (category=2), if present
        mr_comps = [c for c in comps if isinstance(c, dict) and c.get("category") == 2]
        if mr_comps:
            mr_data = data.copy()
            mr_data["BizSpeechComponent"] = mr_comps
            mr_dto = full_to_component_export(mr_data, name=nm, category=2)
            mr_json = json.dumps(mr_dto, ensure_ascii=False, indent=2).encode("utf-8")
            zf.writestr(f"{stem} (multi-round).component.json", mr_json)

        # Intent Excel
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

        # KB Excel
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

    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{stem}.components.zip"'})


@app.get("/session")
def get_session(s: Session = Depends(current_session)):
    return _active_payload(s)


@app.post("/session")
async def create_session(file: UploadFile = File(...),
                         store: SessionStore = Depends(current_store)):
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"upload too large (max {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    filename = file.filename or ""

    # Detect ZIP by filename or magic bytes (PK = 0x50 0x4B).
    is_zip = filename.lower().endswith(".zip") or raw[:2] == b"PK"

    if is_zip:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)
        try:
            bundle = InputBundle.load(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid ZIP export: {e}")
        finally:
            tmp_path.unlink(missing_ok=True)
        data = bundle.data
        comp = is_component_export(data)
        base = data if comp else None
        if comp:
            data = component_export_to_full(data)
        stem = Path(filename).stem or "Imported bot"
        with _exclusive(store.active()):
            store.new(name=stem)
            s = store.active()
            s.load(data, speech_name=bundle.speech_name, wavs=bundle.wavs,
                   is_component=comp, component_base=base)
            s.name = stem
    else:
        data = _parse_or_400(raw)
        comp = is_component_export(data)
        base = data if comp else None
        if comp:
            data = component_export_to_full(data)
        stem = Path(filename).stem or "Imported bot"
        with _exclusive(store.active()):
            store.new(name=stem)
            s = store.active()
            s.load(data, is_component=comp, component_base=base)
            s.name = stem

    s._autosave()
    nm = speechname.read_speech_name(s.current())
    if nm and nm != "Empty Dialogue" and s.id:
        store.rename(s.id, nm)
    # Validate only once; reuse the result for the response.
    findings = agents.validate(data)
    return {
        "summary": agents.summarize(data),
        "findings": findings,
        "is_component": s.is_component,
        "component_warnings": agents.component_export_warnings(s.current()) if s.is_component else [],
    }


@app.get("/samples")
def list_samples_route():
    return samples.list_samples()


@app.post("/samples/{sample_id}")
def load_sample(sample_id: str, store: SessionStore = Depends(current_store)):
    manifest = samples.load_manifest(sample_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="unknown sample")
    built = agents.propose_build(manifest)
    if not built["ok"]:
        raise HTTPException(status_code=500, detail=f"sample build failed: {built.get('error')}")
    title = samples.title_of(sample_id)
    with _exclusive(store.active()):
        store.new(name=title)
        s = store.active()
        s.load(built["proposed_data"])
        s.name = title
        s._autosave()
    data = s.current()
    return {"summary": agents.summarize(data), "findings": agents.validate(data)}


@app.post("/session/blank")
def create_blank_session(store: SessionStore = Depends(current_store)):
    with _exclusive(store.active()):
        store.new(name="New session")
        s = store.active()
        s.load({"BizSpeechComponent": []})
    return {"summary": s.summary(), "findings": s.findings()}


@app.post("/session/clear")
def clear_session(s: Session = Depends(current_session)):
    """Drop the current session so the dashboard returns to the upload/landing screen."""
    s.reset()
    return {"cleared": True}


@app.get("/summary")
async def get_summary(s: Session = Depends(_require_session)):
    return s.summary()


@app.get("/findings")
async def get_findings(s: Session = Depends(_require_session)):
    return s.findings()


@app.get("/intents")
async def get_intents(s: Session = Depends(_require_session)):
    return agents.list_intents(s.current())


@app.get("/node/{uuid}")
async def get_node(uuid: str, s: Session = Depends(_require_session)):
    node = agents.read_node(s.current(), uuid)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node


@app.put("/node/{uuid}/text")
def edit_node_text(uuid: str, body: NodeTextRequest,
                   s: Session = Depends(_require_session)):
    import yaml
    label = (body.label or "").strip()
    prompt = (body.prompt or "").strip()
    if not label and not prompt:
        raise HTTPException(status_code=400, detail="label or prompt required")
    with s._lock:
        idx = _component_index_of(s.current(), uuid)
        if idx is None:
            raise HTTPException(status_code=404, detail="node not found")
        op = {"op": "rename-node", "component": idx, "node": {"uuid": uuid}}
        if label:
            op["label"] = label
        if prompt:
            op["prompt"] = prompt
        r = agents.propose_mods(s.current(), yaml.safe_dump([op]))
        if not r["ok"]:
            raise HTTPException(status_code=400, detail=r["error"])
        s.apply(r["proposed_data"])   # new undoable version + autosave + clears pending
        return {
            "ok": True,
            "summary": s.summary(),
            "findings": s.findings(),
            "can_undo": s.can_undo(),
            "can_redo": s.can_redo(),
            "node": agents.read_node(s.current(), uuid),
        }


@app.post("/chat")
def chat(req: ChatRequest, s: Session = Depends(current_session),
         client: LLMClient = Depends(get_client), cid: str = Depends(client_id)):
    # Sync def → runs in the threadpool, so the event loop stays free for
    # /chat/cancel while this turn holds the lock.
    if not s._stack:
        raise HTTPException(status_code=503, detail="no session loaded")
    cfg = config_store.config_for(cid)
    if s.images and not _model_is_vision(cfg):
        s.images = []
        raise HTTPException(status_code=400,
            detail="the current model can't read images; pick a Claude vision model in Settings")
    # Log the model actually built/sent (catalog-resolved), not the raw cfg —
    # the new UI sends only model_id, so cfg.model is None and the old
    # `cfg.model or LLM_MODEL` would mislabel every turn as the env default.
    provider, model, _ = _resolve_model(cfg)
    t0 = time.perf_counter()
    try:
        with s._lock:
            result = run_turn(client, s, req.message)
    except HTTPException:
        raise
    except Exception as e:
        log.info("", extra={"ev": "llm", "provider": provider, "model": model, "ok": False,
                            "ms": round((time.perf_counter() - t0) * 1000), "err": str(e)})
        raise LLMProviderError(f"LLM provider error: {e}") from e
    log.info("", extra={"ev": "llm", "provider": provider, "model": model, "ok": True,
                        "ms": round((time.perf_counter() - t0) * 1000)})
    s._autosave()
    return result


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, s: Session = Depends(current_session),
                client: LLMClient = Depends(get_client), cid: str = Depends(client_id)):
    if not s._stack:
        raise HTTPException(status_code=503, detail="no session loaded")
    cfg = config_store.config_for(cid)
    if s.images and not _model_is_vision(cfg):
        s.images = []
        raise HTTPException(status_code=400,
            detail="the current model can't read images; pick a Claude vision model in Settings")
    # Catalog-resolved model for the audit log (see /chat note above).
    provider, model, _ = _resolve_model(cfg)

    def _gen():
        t0 = time.perf_counter()
        state = {"ok": True}
        q: queue.Queue = queue.Queue()

        # The turn runs in a worker thread so the SSE loop can emit heartbeats
        # while the turn is blocked on a slow LLM call or a long tool. The worker
        # holds s._lock for the whole turn (single-turn-at-a-time preserved).
        def _worker():
            with s._lock:
                try:
                    for ev in run_turn_stream(client, s, req.message):
                        q.put(("ev", ev))
                except Exception as e:
                    state["ok"] = False
                    log.error("", extra={"ev": "exc", "path": "/chat/stream",
                                         "err": f"{type(e).__name__}: {e}"}, exc_info=e)
                    q.put(("err", str(e)))
                finally:
                    s._autosave()
                    q.put(("end", None))

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        # Immediate byte: commits the 200 + response headers now so the proxy
        # never hits its time-to-first-byte cap, however long the turn takes.
        yield ": open\n\n"
        completed = False
        try:
            while True:
                try:
                    kind, payload = q.get(timeout=_HEARTBEAT_S)
                except queue.Empty:
                    yield ": ping\n\n"      # keepalive during a silent stretch
                    continue
                if kind == "ev":
                    yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
                elif kind == "err":
                    yield f"data: {json.dumps({'type': 'error', 'message': payload})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'canceled': False, 'text': ''})}\n\n"
                else:  # "end"
                    break
            completed = True
        finally:
            # If the loop is torn down before the turn finished (client
            # disconnected -> Starlette closes the generator -> GeneratorExit),
            # signal the worker to stop so it doesn't keep running/spending and
            # holding the lock. It checks cancel_requested between steps.
            if not completed:
                s.cancel_requested = True
            worker.join(timeout=2)
            log.info("", extra={"ev": "llm", "provider": provider, "model": model,
                                "ok": state["ok"], "canceled": not completed,
                                "ms": round((time.perf_counter() - t0) * 1000)})

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.post("/chat/cancel")
def chat_cancel(s: Session = Depends(current_session)):
    # Must NOT take the lock — it runs while a turn holds it.
    s.cancel_requested = True
    return {"canceling": True}


@app.post("/chat/attach")
async def chat_attach(file: UploadFile = File(...), s: Session = Depends(_require_session)):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > _ATTACH_MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 5 MB)")
    name = file.filename or "upload"
    media_type = _image_media_type(name, raw)
    if media_type is not None:
        if len(s.images) >= _MAX_IMAGES:
            raise HTTPException(status_code=400, detail=f"too many images (max {_MAX_IMAGES})")
        import base64 as _b64
        s.images.append({"name": name, "media_type": media_type,
                         "data": _b64.b64encode(raw).decode("ascii")})
        return {"name": name, "kind": "image", "count": len(s.images)}
    # non-image → existing single-attachment path
    prior = s.attachment
    if prior and prior.get("path"):
        Path(prior["path"]).unlink(missing_ok=True)
    suffix = Path(name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    kind, excerpt = _classify_attachment(name, tmp_path)
    s.attachment = {"name": name, "path": tmp_path, "kind": kind, "excerpt": excerpt}
    return {"name": name, "kind": kind}


@app.delete("/chat/attach")
async def chat_clear_attach(kind: str | None = None, index: int | None = None,
                            s: Session = Depends(_require_session)):
    if kind == "image":
        if index is None:
            s.images = []
        elif 0 <= index < len(s.images):
            s.images.pop(index)
        return {"cleared": True, "count": len(s.images)}
    if s.attachment and s.attachment.get("path"):
        Path(s.attachment["path"]).unlink(missing_ok=True)
    s.attachment = None
    return {"cleared": True}


# NOTE: these mutators are sync `def` (not async) on purpose. They take the
# per-session threading lock (held by an in-flight chat turn); blocking on it
# must happen in the threadpool, never on the event loop. They do no awaits.
@app.post("/apply")
def apply_pending(s: Session = Depends(_require_session),
                  store: SessionStore = Depends(current_store)):
    with s._lock:
        if s.pending is None:
            raise HTTPException(status_code=409, detail="no pending proposal")
        s.apply(s.pending["proposed_data"])
        nm = speechname.read_speech_name(s.current())
        if nm and s.id:
            store.rename(s.id, nm)
        return {
            "applied": True,
            "bot_name": nm,
            "summary": s.summary(),
            "findings": s.findings(),
            "can_undo": s.can_undo(),
            "can_redo": s.can_redo(),
        }


@app.post("/undo")
def undo(s: Session = Depends(_require_session),
         store: SessionStore = Depends(current_store)):
    with s._lock:
        ok = s.undo()
        nm = speechname.read_speech_name(s.current())
        if nm and s.id:
            store.rename(s.id, nm)
        return {
            "ok": ok,
            "bot_name": nm,
            "summary": s.summary(),
            "findings": s.findings(),
            "can_undo": s.can_undo(),
            "can_redo": s.can_redo(),
        }


@app.post("/redo")
def redo(s: Session = Depends(_require_session),
         store: SessionStore = Depends(current_store)):
    with s._lock:
        ok = s.redo()
        nm = speechname.read_speech_name(s.current())
        if nm and s.id:
            store.rename(s.id, nm)
        return {
            "ok": ok,
            "bot_name": nm,
            "summary": s.summary(),
            "findings": s.findings(),
            "can_undo": s.can_undo(),
            "can_redo": s.can_redo(),
        }


@app.put("/speech-name")
def set_speech_name_route(body: BotNameRequest,
                          s: Session = Depends(_require_session),
                          store: SessionStore = Depends(current_store)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be empty")
    with s._lock:
        new = speechname.set_speech_name(s.current(), name)
        s.apply(new)                              # new undoable version + autosave
        s.speech_name = speechname.slugify_filename(name)
        if s.id:
            store.rename(s.id, name)              # mirror the session label (persists snapshot)
        return {
            "ok": True,
            "bot_name": name,
            "summary": s.summary(),
            "findings": s.findings(),
            "can_undo": s.can_undo(),
            "can_redo": s.can_redo(),
        }


# ---------------------------------------------------------------------------
# Multi-session management routes
# ---------------------------------------------------------------------------

@app.get("/sessions")
def list_sessions_route(store: SessionStore = Depends(current_store)):
    return {"sessions": store.list(), "active_id": store.active().id}


@app.post("/sessions")
def create_session_slot(store: SessionStore = Depends(current_store)):
    with _exclusive(store.active()):
        store.new()
        store.active().load({"BizSpeechComponent": []})
    return _active_payload(store.active())


@app.post("/sessions/{sid}/activate")
def activate_session(sid: str, store: SessionStore = Depends(current_store)):
    with _exclusive(store.active()):
        if not store.activate(sid):
            raise HTTPException(status_code=404, detail="session not found")
    return _active_payload(store.active())


@app.patch("/sessions/{sid}")
def rename_session(sid: str, body: RenameRequest,
                   store: SessionStore = Depends(current_store)):
    if not store.rename(sid, body.name):
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}


@app.delete("/sessions/{sid}")
def delete_session_route(sid: str, store: SessionStore = Depends(current_store)):
    store.delete(sid)
    return {"ok": True, "active": store.active().id}


# ---------------------------------------------------------------------------
# SPA mount — must come LAST so all API routes take precedence.
# Guarded on dir existence so dev (no built frontend) still runs.
# ---------------------------------------------------------------------------

_STATIC = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC):
    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="spa")
