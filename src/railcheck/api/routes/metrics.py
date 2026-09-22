from __future__ import annotations

from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def prometheus_metrics(request: Request) -> Response:
    body = request.app.state.metrics.render_prometheus()
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")
