from __future__ import annotations

import json

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import agents
from session import Session

app = FastAPI(title="Talkbot Architect API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SESSION = Session()


@app.get("/health")
async def health():
    return {"status": "ok"}


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


@app.post("/session")
async def create_session(file: UploadFile = File(...)):
    data = _parse_or_400(await file.read())
    SESSION.load(data)
    return {"summary": agents.summarize(data), "findings": agents.validate(data)}


@app.get("/summary")
async def get_summary():
    return agents.summarize(SESSION.current())


@app.get("/findings")
async def get_findings():
    return agents.validate(SESSION.current())


@app.get("/node/{uuid}")
async def get_node(uuid: str):
    node = agents.read_node(SESSION.current(), uuid)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    return node
