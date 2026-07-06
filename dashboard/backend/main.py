from __future__ import annotations

# Load .env before anything reads os.environ — python-dotenv no-ops when
# no .env is present, so this is safe in production too.
from dotenv import load_dotenv
load_dotenv()

import json  # noqa: E402
import time  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402
import io  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.requests import Request  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import agents  # noqa: E402
import backup  # noqa: E402
import config_store  # noqa: E402
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
_STARTED = time.time()

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
    message: str


class ConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    show_reasoning: Optional[bool] = None


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

def _require_session(s: Session = Depends(current_session)) -> Session:
    """Raise 503 if no data has been loaded into the active session yet."""
    if not s._stack:
        raise HTTPException(status_code=503, detail="no session loaded")
    return s


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
    """Return the rehydrate payload for the current active session."""
    if not s._stack:
        return {"summary": None, "id": s.id, "bot_name": None}
    data = s.current()
    return {
        "id": s.id,
        "bot_name": speechname.read_speech_name(data),
        "summary": agents.summarize(data),
        "findings": agents.validate(data),
        "transcript": _reconstruct_transcript(s.transcript),
        "proposal": s.pending,
        "can_undo": s.can_undo(),
        "can_redo": s.can_redo(),
        "usage": s.usage,
    }


def _parse_or_400(content: bytes) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    try:
        agents.validate(data)  # also forces a parse; raises on bad structure
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Talkbot export: {e}")
    return data


def get_client(cid: str = Depends(client_id)) -> LLMClient:
    """Build an LLMClient from per-client config overrides + env fallbacks."""
    cfg = config_store.config_for(cid)
    provider = cfg.provider or os.environ.get("LLM_PROVIDER")
    model = cfg.model or os.environ.get("LLM_MODEL")
    base_url = cfg.base_url
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
    provider = cfg.provider or os.environ.get("LLM_PROVIDER")
    model = cfg.model or os.environ.get("LLM_MODEL")
    base_url = cfg.base_url or os.environ.get(
        "ANTHROPIC_BASE_URL" if (provider or "anthropic").lower() == "anthropic" else "OPENAI_BASE_URL"
    )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "key_set": effective_key_set(provider, cfg),
        "source": "override" if any_override(cfg) else "env",
        "show_reasoning": cfg.show_reasoning,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "live_sessions": len(REGISTRY._stores), "uptime_s": int(time.time() - _STARTED)}


@app.get("/admin/backup")
async def admin_backup():
    data, filename = backup.open_backup_stream()
    log.info("", extra={"ev": "backup", "kind": "download", "bytes": len(data)})
    return Response(content=data, media_type="application/gzip",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/admin/restore")
async def admin_restore(file: UploadFile = File(...)):
    if not os.environ.get("DASHBOARD_PASSWORD"):
        raise HTTPException(status_code=403, detail="restore requires DASHBOARD_PASSWORD to be set")
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
        cfg.base_url = update.base_url
    # Empty string means "leave unchanged"; only update when truthy
    if update.api_key:
        cfg.api_key = update.api_key
    if update.show_reasoning is not None:
        cfg.show_reasoning = update.show_reasoning
    return _config_response(cfg)


@app.post("/config/clear")
async def clear_config(cid: str = Depends(client_id)):
    """Reset all CONFIG overrides — effective config reverts to env vars."""
    cfg = config_store.config_for(cid)
    cfg.provider = cfg.model = cfg.base_url = cfg.api_key = None
    cfg.show_reasoning = True
    return _config_response(cfg)


@app.get("/export")
async def export_current(s: Session = Depends(_require_session)):
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


@app.get("/session")
def get_session(s: Session = Depends(current_session)):
    return _active_payload(s)


@app.post("/session")
async def create_session(file: UploadFile = File(...),
                         store: SessionStore = Depends(current_store)):
    raw = await file.read()
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
    return {"summary": agents.summarize(data), "findings": findings}


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
    store.new(name=title)
    s = store.active()
    s.load(built["proposed_data"])
    s.name = title
    s._autosave()
    data = s.current()
    return {"summary": agents.summarize(data), "findings": agents.validate(data)}


@app.post("/session/blank")
def create_blank_session(store: SessionStore = Depends(current_store)):
    store.new(name="New session")
    s = store.active()
    s.load({"BizSpeechComponent": []})
    data = s.current()
    return {"summary": agents.summarize(data), "findings": agents.validate(data)}


@app.post("/session/clear")
def clear_session(s: Session = Depends(current_session)):
    """Drop the current session so the dashboard returns to the upload/landing screen."""
    s.reset()
    return {"cleared": True}


@app.get("/summary")
async def get_summary(s: Session = Depends(_require_session)):
    return agents.summarize(s.current())


@app.get("/findings")
async def get_findings(s: Session = Depends(_require_session)):
    return agents.validate(s.current())


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
        "summary": agents.summarize(s.current()),
        "findings": agents.validate(s.current()),
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
    provider = cfg.provider or os.environ.get("LLM_PROVIDER")
    model = cfg.model or os.environ.get("LLM_MODEL")
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
    provider = cfg.provider or os.environ.get("LLM_PROVIDER")
    model = cfg.model or os.environ.get("LLM_MODEL")

    def _gen():
        t0 = time.perf_counter()
        ok = True
        with s._lock:
            try:
                for ev in run_turn_stream(client, s, req.message):
                    yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
            except Exception as e:
                ok = False
                log.error("", extra={"ev": "exc", "path": "/chat/stream", "err": f"{type(e).__name__}: {e}"}, exc_info=e)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'canceled': False, 'text': ''})}\n\n"
            finally:
                s._autosave()
                log.info("", extra={"ev": "llm", "provider": provider, "model": model, "ok": ok,
                                    "ms": round((time.perf_counter() - t0) * 1000)})

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.post("/chat/cancel")
def chat_cancel(s: Session = Depends(current_session)):
    # Must NOT take the lock — it runs while a turn holds it.
    s.cancel_requested = True
    return {"canceling": True}


@app.post("/apply")
async def apply_pending(s: Session = Depends(_require_session),
                        store: SessionStore = Depends(current_store)):
    if s.pending is None:
        raise HTTPException(status_code=409, detail="no pending proposal")
    s.apply(s.pending["proposed_data"])
    nm = speechname.read_speech_name(s.current())
    if nm and s.id:
        store.rename(s.id, nm)
    return {
        "applied": True,
        "bot_name": nm,
        "summary": agents.summarize(s.current()),
        "findings": agents.validate(s.current()),
        "can_undo": s.can_undo(),
        "can_redo": s.can_redo(),
    }


@app.post("/undo")
async def undo(s: Session = Depends(_require_session),
               store: SessionStore = Depends(current_store)):
    ok = s.undo()
    nm = speechname.read_speech_name(s.current())
    if nm and s.id:
        store.rename(s.id, nm)
    return {
        "ok": ok,
        "bot_name": nm,
        "summary": agents.summarize(s.current()),
        "findings": agents.validate(s.current()),
        "can_undo": s.can_undo(),
        "can_redo": s.can_redo(),
    }


@app.post("/redo")
async def redo(s: Session = Depends(_require_session),
               store: SessionStore = Depends(current_store)):
    ok = s.redo()
    nm = speechname.read_speech_name(s.current())
    if nm and s.id:
        store.rename(s.id, nm)
    return {
        "ok": ok,
        "bot_name": nm,
        "summary": agents.summarize(s.current()),
        "findings": agents.validate(s.current()),
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
    new = speechname.set_speech_name(s.current(), name)
    s.apply(new)                                  # new undoable version + autosave
    s.speech_name = speechname.slugify_filename(name)
    if s.id:
        store.rename(s.id, name)                  # mirror the session label (persists snapshot)
    return {
        "ok": True,
        "bot_name": name,
        "summary": agents.summarize(s.current()),
        "findings": agents.validate(s.current()),
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
    store.new()
    store.active().load({"BizSpeechComponent": []})
    return _active_payload(store.active())


@app.post("/sessions/{sid}/activate")
def activate_session(sid: str, store: SessionStore = Depends(current_store)):
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
