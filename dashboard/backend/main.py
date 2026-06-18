from fastapi import FastAPI

app = FastAPI(title="Talkbot Architect API")

@app.get("/health")
async def health():
    return {"status": "ok"}
