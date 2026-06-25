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
from config_store import CONFIG, any_override, effective_key_set
from llm.base import LLMClient
from llm.factory import LLMConfigError, make_client
from orchestrator import run_turn, run_turn_stream
from session import Session
from wizmodifier.io import InputBundle

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

SESSION = Session()


@app.on_event("startup")
def _load_persisted_session() -> None:
    if not SESSION._stack:
        persistence.load_session(SESSION)


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


# ---------------------------------------------------------------------------
# Helpers / dependencies
# ---------------------------------------------------------------------------

def _require_session() -> None:
    """Raise 503 if no data has been loaded into SESSION yet."""
    if not SESSION._stack:
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
    payload = json.dumps(SESSION.current(), ensure_ascii=False, separators=(",", ":"))
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={SESSION.speech_name}"},
    )


@app.get("/session")
def get_session():
    if not SESSION._stack:
        return {"summary": None}
    data = SESSION.current()
    return {
        "summary": agents.summarize(data),
        "findings": agents.validate(data),
        "transcript": _reconstruct_transcript(SESSION.transcript),
        "proposal": SESSION.pending,
        "can_undo": SESSION.can_undo(),
        "can_redo": SESSION.can_redo(),
    }


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
        SESSION.load(data, speech_name=bundle.speech_name, wavs=bundle.wavs)
    else:
        data = _parse_or_400(raw)
        SESSION.load(data)

    # Validate only once; reuse the result for the response.
    findings = agents.validate(data)
    return {"summary": agents.summarize(data), "findings": findings}


@app.post("/session/blank")
def create_blank_session():
    SESSION.load({"BizSpeechComponent": []})
    data = SESSION.current()
    return {"summary": agents.summarize(data), "findings": agents.validate(data)}


@app.post("/session/clear")
def clear_session():
    """Drop the current session so the dashboard returns to the upload/landing screen."""
    SESSION.reset()
    return {"cleared": True}


@app.get("/summary")
async def get_summary():
    _require_session()
    return agents.summarize(SESSION.current())


@app.get("/findings")
async def get_findings():
    _require_session()
    return agents.validate(SESSION.current())


@app.get("/node/{uuid}")
async def get_node(uuid: str):
    _require_session()
    node = agents.read_node(SESSION.current(), uuid)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node


@app.post("/chat")
def chat(req: ChatRequest, client: LLMClient = Depends(get_client)):
    # Sync def → runs in the threadpool, so the event loop stays free for
    # /chat/cancel while this turn holds the lock.
    _require_session()
    try:
        with SESSION._lock:
            result = run_turn(client, SESSION, req.message)
    except HTTPException:
        raise
    except Exception as e:
        raise LLMProviderError(f"LLM provider error: {e}") from e
    SESSION._autosave()
    return result


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, client: LLMClient = Depends(get_client)):
    _require_session()

    def _gen():
        with SESSION._lock:
            try:
                for ev in run_turn_stream(client, SESSION, req.message):
                    yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
            except Exception as e:  # surface provider/tool failure as an SSE error, not a 500
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'canceled': False, 'text': ''})}\n\n"
            finally:
                SESSION._autosave()

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.post("/chat/cancel")
def chat_cancel():
    # Must NOT take the lock — it runs while a turn holds it.
    SESSION.cancel_requested = True
    return {"canceling": True}


@app.post("/apply")
async def apply_pending():
    _require_session()
    if SESSION.pending is None:
        raise HTTPException(status_code=409, detail="no pending proposal")
    SESSION.apply(SESSION.pending["proposed_data"])
    return {
        "applied": True,
        "summary": agents.summarize(SESSION.current()),
        "findings": agents.validate(SESSION.current()),
        "can_undo": SESSION.can_undo(),
        "can_redo": SESSION.can_redo(),
    }


@app.post("/undo")
async def undo():
    _require_session()
    ok = SESSION.undo()
    return {
        "ok": ok,
        "summary": agents.summarize(SESSION.current()),
        "findings": agents.validate(SESSION.current()),
        "can_undo": SESSION.can_undo(),
        "can_redo": SESSION.can_redo(),
    }


@app.post("/redo")
async def redo():
    _require_session()
    ok = SESSION.redo()
    return {
        "ok": ok,
        "summary": agents.summarize(SESSION.current()),
        "findings": agents.validate(SESSION.current()),
        "can_undo": SESSION.can_undo(),
        "can_redo": SESSION.can_redo(),
    }
