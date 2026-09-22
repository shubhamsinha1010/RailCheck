from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from railcheck.api.deps import get_gate_service, get_settings
from railcheck.api.schemas import (
    AnswerOut,
    GateBatchCheckRequest,
    GateBatchCheckResponse,
    GateCheckRequest,
    GateCheckResponse,
)
from railcheck.application.gate_service import GateService
from railcheck.config import Settings
from railcheck.domain.models import GateContext, GateResult

router = APIRouter(tags=["gate"])


def _to_response(result: GateResult) -> GateCheckResponse:
    return GateCheckResponse(
        request_id=str(result.request_id),
        action=result.action,
        reason=result.reason,
        triggered_by=result.triggered_by,
        pack=result.pack_name,
        backend=result.backend,
        answers=[
            AnswerOut(
                key=a.key,
                type=a.type.value,
                value=a.value,
                confidence=a.confidence,
                probabilities=a.probabilities,
            )
            for a in result.answers
        ],
        created_at=result.created_at.isoformat(),
    )


def _to_context(body: GateCheckRequest) -> GateContext:
    return GateContext(
        candidate_output=body.candidate_output,
        user_prompt=body.user_prompt,
        tool_name=body.tool_name,
        tool_args=body.tool_args,
        metadata=body.metadata,
    )


@router.post("/v1/check", response_model=GateCheckResponse)
def check_output(
    body: GateCheckRequest,
    service: Annotated[GateService, Depends(get_gate_service)],
) -> GateCheckResponse:
    return _to_response(service.check(_to_context(body)))


@router.post("/v1/check/batch", response_model=GateBatchCheckResponse)
def check_output_batch(
    body: GateBatchCheckRequest,
    service: Annotated[GateService, Depends(get_gate_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GateBatchCheckResponse:
    if len(body.items) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch size {len(body.items)} exceeds max_batch_size={settings.max_batch_size}",
        )
    results = service.check_batch([_to_context(item) for item in body.items])
    return GateBatchCheckResponse(results=[_to_response(r) for r in results], count=len(results))
