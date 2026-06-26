# Talkbot Architect dashboard — single-container, single-tenant deploy.
# Multi-stage: build the React SPA, then a Python runtime that serves it
# same-origin from FastAPI and imports the four skills via the repo layout.

# ---- stage 1: build frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY dashboard/frontend/package*.json ./
RUN npm ci
COPY dashboard/frontend/ ./
# Same-origin API base: empty VITE_API_URL -> api.js resolves BASE='' (relative paths).
RUN VITE_API_URL="" npm run build          # -> /fe/dist

# ---- stage 2: python runtime ----
FROM python:3.11-slim AS runtime
WORKDIR /app

# Backend + skill runtime deps (skills are sys.path-imported, not pip packages,
# so their third-party deps live in requirements.txt). uvicorn[standard] for prod.
COPY dashboard/backend/requirements.txt ./req.txt
RUN pip install --no-cache-dir -r req.txt "uvicorn[standard]"

# Preserve the repo layout so paths.py `parents[2]` of /app/dashboard/backend == /app,
# resolving /app/.claude/skills at runtime.
COPY .claude/skills/ /app/.claude/skills/
COPY dashboard/backend/ /app/dashboard/backend/

# Built SPA into the dir main.py serves via StaticFiles (os.path.dirname(__file__)/static).
COPY --from=frontend /fe/dist/ /app/dashboard/backend/static/

WORKDIR /app/dashboard/backend
EXPOSE 8000
# Single worker — the backend has a process-global active Session + in-memory config.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
