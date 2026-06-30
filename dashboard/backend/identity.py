"""Anonymous per-browser identity: a `tbid` cookie keys each workspace."""
from __future__ import annotations

import os
import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE = "tbid"


class ClientCookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.cookies.get(COOKIE)
        minted = False
        if not cid:
            cid = secrets.token_urlsafe(16)
            minted = True
        request.state.tbid = cid
        response = await call_next(request)
        if minted:
            response.set_cookie(
                COOKIE, cid, httponly=True, samesite="lax", path="/",
                secure=os.environ.get("COOKIE_SECURE") == "1",
            )
        return response


def client_id(request: Request) -> str:
    # Middleware always sets this; fall back defensively.
    return getattr(request.state, "tbid", "_legacy")
