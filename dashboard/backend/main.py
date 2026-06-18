from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import json
import sys
from pathlib import Path
from dataclasses import asdict

app = FastAPI(title="Talkbot Architect API")

class ChatRequest(BaseModel):
    message: str
    context: dict | None = None

@app.post("/chat")
async def chat(req: ChatRequest):
    # This is a stub for the 9-hour MVP. 
    # Real implementation would call OpenAI/Gemini with the findings context.
    context = req.context or {}
    return {"response": f"I see you have {context.get('errors', 0)} errors. How can I help?"}

# Add project root to path to import wizcheck
# Project root is ../../ relative to dashboard/backend/main.py
sys.path.append(str(Path(__file__).parent.parent.parent / ".claude/skills/wiz-checker/scripts"))
from wizcheck.parser import parse_dict
from wizcheck.checks import run_all_checks

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    raw_data = json.loads(content)
    bot = parse_dict(raw_data)
    findings = run_all_checks(bot)
    
    # Simple summary calculation
    errors = len([f for f in findings if f.severity == "error"])
    warnings = len([f for f in findings if f.severity == "warning"])
    
    return {
        "summary": {"errors": errors, "warnings": warnings},
        "findings": [asdict(f) for f in findings]
    }
