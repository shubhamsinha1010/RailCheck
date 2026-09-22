from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["demo"])

_DEMO = Path(__file__).resolve().parents[2] / "static" / "demo.html"


@router.get("/demo")
def demo_page() -> FileResponse:
    return FileResponse(_DEMO, media_type="text/html")
