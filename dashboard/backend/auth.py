"""Shared-password gate. Active only when DASHBOARD_PASSWORD is set."""
from __future__ import annotations

import base64
import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_EXEMPT = {"/health"}


class PasswordGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        password = os.environ.get("DASHBOARD_PASSWORD")
        if not password or request.url.path in _EXEMPT:
            return await call_next(request)
        user = os.environ.get("DASHBOARD_USER", "admin")
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header[6:]).decode("utf-8")
                got_user, _, got_pw = decoded.partition(":")
                if hmac.compare_digest(got_user, user) and hmac.compare_digest(got_pw, password):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Talkbot Architect"'},
        )
