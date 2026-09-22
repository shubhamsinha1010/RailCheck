from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz(request: Request) -> dict[str, str]:
    return {
        "status": "ok",
        "backend": request.app.state.gate_service.backend_name,
        "pack": request.app.state.gate_service.pack_name,
    }
