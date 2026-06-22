from __future__ import annotations

import json
import os

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import agents
from llm.base import LLMClient
from llm.factory import LLMConfigError, make_client
from orchestrator import run_turn
from session import Session

app = FastAPI(title="Talkbot Architect API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SESSION = Session()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers / dependencies
# ---------------------------------------------------------------------------

def _require_session() -> None:
    """Raise 503 if no data has been loaded into SESSION yet."""
    if not SESSION._stack:
        raise HTTPException(status_code=503, detail="no session loaded")


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
    try:
        return make_client(
            provider=os.environ.get("LLM_PROVIDER"),
            api_key=None,
            model=os.environ.get("LLM_MODEL"),
        )
    except LLMConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/session")
async def create_session(file: UploadFile = File(...)):
    data = _parse_or_400(await file.read())
    SESSION.load(data)
    # Validate only once; reuse the result for the response.
    findings = agents.validate(data)
    return {"summary": agents.summarize(data), "findings": findings}


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
async def chat(req: ChatRequest, client: LLMClient = Depends(get_client)):
    _require_session()
    return run_turn(client, SESSION, req.message)


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
