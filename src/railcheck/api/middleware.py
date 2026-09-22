from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Paths that stay public even when an API key is configured.
_PUBLIC_PREFIXES = (
    "/healthz",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/demo",
)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """
    Optional shared-secret auth.

    When settings.api_key is empty, all requests pass (local/dev default).
    When set, require Authorization: Bearer <key> or X-API-Key header.
    """

    def __init__(self, app, api_key: str) -> None:  # noqa: ANN001
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._api_key or self._is_public(request.url.path):
            return await call_next(request)

        presented = self._extract_key(request)
        if presented is None or not secrets.compare_digest(presented, self._api_key):
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)
        return await call_next(request)

    @staticmethod
    def _is_public(path: str) -> bool:
        return any(path == p or path.startswith(f"{p}/") for p in _PUBLIC_PREFIXES)

    @staticmethod
    def _extract_key(request: Request) -> str | None:
        header = request.headers.get("x-api-key")
        if header:
            return header.strip()
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None
