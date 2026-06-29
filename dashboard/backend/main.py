from __future__ import annotations

# Load .env before anything reads os.environ — python-dotenv no-ops when
# no .env is present, so this is safe in production too.
from dotenv import load_dotenv
load_dotenv()

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

import agents
import config_store
import persistence
import speechname
from config_store import CONFIG, any_override, effective_key_set
from llm.base import LLMClient
from llm.factory import LLMConfigError, make_client
from orchestrator import run_turn, run_turn_stream
from session_store import SessionStore
from wizmodifier.io import InputBundle, write_output

app = FastAPI(title="Talkbot Architect API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _error_body(exc: Exception) -> dict:
    return {"error": {"type": type(exc).__name__, "message": str(exc)}}


class LLMProviderError(Exception):
    """Wraps an upstream LLM/provider failure so the handler can return 502."""


@app.exception_handler(LLMProviderError)
async def _provider_error(request: Request, exc: LLMProviderError):
    return JSONResponse(status_code=502, content=_error_body(exc))


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content=_error_body(exc))

STORE = SessionStore()
SESSION = STORE.active()        # module alias — the live active object


def _S():
    """Return the currently active Session (read at call time, not import time)."""
    return STORE.active()


@app.on_event("startup")
def _load_persisted_session() -> None:
    STORE.boot()


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

def _require_session() -> None:
    """Raise 503 if no data has been loaded into the active session yet."""
    if not _S()._stack:
        raise HTTPException(status_code=503, detail="no session loaded")


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


def _active_payload() -> dict:
    """Return the rehydrate payload for the current active session."""
    s = _S()
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


def get_client() -> LLMClient:
    """Build an LLMClient from CONFIG overrides + env fallbacks."""
    provider = CONFIG.provider or os.environ.get("LLM_PROVIDER")
    model = CONFIG.model or os.environ.get("LLM_MODEL")
    base_url = CONFIG.base_url  # factory also falls back to *_BASE_URL env vars
    api_key = CONFIG.api_key    # factory falls back to provider env key when None
    try:
        return make_client(provider=provider, api_key=api_key, model=model, base_url=base_url)
    except LLMConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))


def _config_response() -> dict:
    """Build the /config response body. NEVER includes the api_key value."""
    provider = CONFIG.provider or os.environ.get("LLM_PROVIDER")
    model = CONFIG.model or os.environ.get("LLM_MODEL")
    base_url = CONFIG.base_url or os.environ.get(
        "ANTHROPIC_BASE_URL" if (provider or "anthropic").lower() == "anthropic" else "OPENAI_BASE_URL"
    )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "key_set": effective_key_set(provider),
        "source": "override" if any_override() else "env",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/config")
async def get_config():
    """Return current effective LLM config. api_key value is NEVER included."""
    return _config_response()


@app.put("/config")
async def put_config(update: ConfigUpdate):
    """Override any subset of provider/model/base_url/api_key in memory.

    An empty-string api_key is treated as 'leave unchanged' (not a clear).
    Returns the same shape as GET /config.
    """
    if update.provider is not None:
        CONFIG.provider = update.provider
    if update.model is not None:
        CONFIG.model = update.model
    if update.base_url is not None:
        CONFIG.base_url = update.base_url
    # Empty string means "leave unchanged"; only update when truthy
    if update.api_key:
        CONFIG.api_key = update.api_key
    return _config_response()


@app.post("/config/clear")
async def clear_config():
    """Reset all CONFIG overrides — effective config reverts to env vars."""
    CONFIG.provider = None
    CONFIG.model = None
    CONFIG.base_url = None
    CONFIG.api_key = None
    return _config_response()


@app.get("/export")
async def export_current(_: None = Depends(_require_session)):
    data = _S().current()
    nm = speechname.read_speech_name(data)
    base = speechname.slugify_filename(nm).removesuffix(".json") if nm else "speech_export"
    # Internal entry MUST be a speech*.json (WIZ + InputBundle.load require it);
    # the slugged <base> is only the download filename, never the zip entry.
    sn = _S().speech_name if (_S().speech_name.startswith("speech")
                              and _S().speech_name.endswith(".json")) else "speech_export.json"

    if _S().wavs:  # has audio → import-ready ZIP via the engine writer
        bundle = InputBundle(data=data, speech_name=sn, wavs=_S().wavs)
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
def get_session():
    return _active_payload()


@app.post("/session")
async def create_session(file: UploadFile = File(...)):
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
        stem = Path(filename).stem or "Imported bot"
        STORE.new(name=stem)
        _S().load(data, speech_name=bundle.speech_name, wavs=bundle.wavs)
        _S().name = stem
    else:
        data = _parse_or_400(raw)
        stem = Path(filename).stem or "Imported bot"
        STORE.new(name=stem)
        _S().load(data)
        _S().name = stem

    _S()._autosave()
    nm = speechname.read_speech_name(_S().current())
    if nm and nm != "Empty Dialogue" and _S().id:
        STORE.rename(_S().id, nm)
    # Validate only once; reuse the result for the response.
    findings = agents.validate(data)
    return {"summary": agents.summarize(data), "findings": findings}


@app.post("/session/blank")
def create_blank_session():
    STORE.new(name="New session")
    _S().load({"BizSpeechComponent": []})
    data = _S().current()
    return {"summary": agents.summarize(data), "findings": agents.validate(data)}


@app.post("/session/clear")
def clear_session():
    """Drop the current session so the dashboard returns to the upload/landing screen."""
    _S().reset()
    return {"cleared": True}


@app.get("/summary")
async def get_summary():
    _require_session()
    return agents.summarize(_S().current())


@app.get("/findings")
async def get_findings():
    _require_session()
    return agents.validate(_S().current())


@app.get("/node/{uuid}")
async def get_node(uuid: str):
    _require_session()
    node = agents.read_node(_S().current(), uuid)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node


@app.put("/node/{uuid}/text")
def edit_node_text(uuid: str, body: NodeTextRequest):
    import yaml
    _require_session()
    label = (body.label or "").strip()
    prompt = (body.prompt or "").strip()
    if not label and not prompt:
        raise HTTPException(status_code=400, detail="label or prompt required")
    idx = _component_index_of(_S().current(), uuid)
    if idx is None:
        raise HTTPException(status_code=404, detail="node not found")
    op = {"op": "rename-node", "component": idx, "node": {"uuid": uuid}}
    if label:
        op["label"] = label
    if prompt:
        op["prompt"] = prompt
    r = agents.propose_mods(_S().current(), yaml.safe_dump([op]))
    if not r["ok"]:
        raise HTTPException(status_code=400, detail=r["error"])
    _S().apply(r["proposed_data"])   # new undoable version + autosave + clears pending
    return {
        "ok": True,
        "summary": agents.summarize(_S().current()),
        "findings": agents.validate(_S().current()),
        "can_undo": _S().can_undo(),
        "can_redo": _S().can_redo(),
        "node": agents.read_node(_S().current(), uuid),
    }


@app.post("/chat")
def chat(req: ChatRequest, client: LLMClient = Depends(get_client)):
    # Sync def → runs in the threadpool, so the event loop stays free for
    # /chat/cancel while this turn holds the lock.
    _require_session()
    try:
        with _S()._lock:
            result = run_turn(client, _S(), req.message)
    except HTTPException:
        raise
    except Exception as e:
        raise LLMProviderError(f"LLM provider error: {e}") from e
    _S()._autosave()
    return result


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, client: LLMClient = Depends(get_client)):
    _require_session()

    def _gen():
        with _S()._lock:
            try:
                for ev in run_turn_stream(client, _S(), req.message):
                    yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
            except Exception as e:  # surface provider/tool failure as an SSE error, not a 500
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'canceled': False, 'text': ''})}\n\n"
            finally:
                _S()._autosave()

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.post("/chat/cancel")
def chat_cancel():
    # Must NOT take the lock — it runs while a turn holds it.
    _S().cancel_requested = True
    return {"canceling": True}


@app.post("/apply")
async def apply_pending():
    _require_session()
    if _S().pending is None:
        raise HTTPException(status_code=409, detail="no pending proposal")
    _S().apply(_S().pending["proposed_data"])
    nm = speechname.read_speech_name(_S().current())
    if nm and _S().id:
        STORE.rename(_S().id, nm)
    return {
        "applied": True,
        "bot_name": nm,
        "summary": agents.summarize(_S().current()),
        "findings": agents.validate(_S().current()),
        "can_undo": _S().can_undo(),
        "can_redo": _S().can_redo(),
    }


@app.post("/undo")
async def undo():
    _require_session()
    ok = _S().undo()
    nm = speechname.read_speech_name(_S().current())
    if nm and _S().id:
        STORE.rename(_S().id, nm)
    return {
        "ok": ok,
        "bot_name": nm,
        "summary": agents.summarize(_S().current()),
        "findings": agents.validate(_S().current()),
        "can_undo": _S().can_undo(),
        "can_redo": _S().can_redo(),
    }


@app.post("/redo")
async def redo():
    _require_session()
    ok = _S().redo()
    nm = speechname.read_speech_name(_S().current())
    if nm and _S().id:
        STORE.rename(_S().id, nm)
    return {
        "ok": ok,
        "bot_name": nm,
        "summary": agents.summarize(_S().current()),
        "findings": agents.validate(_S().current()),
        "can_undo": _S().can_undo(),
        "can_redo": _S().can_redo(),
    }


@app.put("/speech-name")
def set_speech_name_route(body: BotNameRequest):
    _require_session()
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be empty")
    new = speechname.set_speech_name(_S().current(), name)
    _S().apply(new)                                  # new undoable version + autosave
    _S().speech_name = speechname.slugify_filename(name)
    if _S().id:
        STORE.rename(_S().id, name)                  # mirror the session label (persists snapshot)
    return {
        "ok": True,
        "bot_name": name,
        "summary": agents.summarize(_S().current()),
        "findings": agents.validate(_S().current()),
        "can_undo": _S().can_undo(),
        "can_redo": _S().can_redo(),
    }


# ---------------------------------------------------------------------------
# Multi-session management routes
# ---------------------------------------------------------------------------

@app.get("/sessions")
def list_sessions_route():
    return {"sessions": STORE.list(), "active_id": persistence.read_active()}


@app.post("/sessions")
def create_session_slot():
    STORE.new()
    _S().load({"BizSpeechComponent": []})
    return _active_payload()   # already carries the new session's id


@app.post("/sessions/{sid}/activate")
def activate_session(sid: str):
    if not STORE.activate(sid):
        raise HTTPException(status_code=404, detail="session not found")
    return _active_payload()   # id == sid, carried by the payload


@app.patch("/sessions/{sid}")
def rename_session(sid: str, body: RenameRequest):
    if not STORE.rename(sid, body.name):
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}


@app.delete("/sessions/{sid}")
def delete_session_route(sid: str):
    STORE.delete(sid)
    return {"ok": True, "active": _S().id}
