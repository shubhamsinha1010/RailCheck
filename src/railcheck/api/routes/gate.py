from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from railcheck.api.deps import get_gate_service
from railcheck.api.schemas import AnswerOut, GateCheckRequest, GateCheckResponse
from railcheck.application.gate_service import GateService
from railcheck.domain.models import GateContext

router = APIRouter(tags=["gate"])


@router.post("/v1/check", response_model=GateCheckResponse)
def check_output(
    body: GateCheckRequest,
    service: Annotated[GateService, Depends(get_gate_service)],
) -> GateCheckResponse:
    context = GateContext(
        candidate_output=body.candidate_output,
        user_prompt=body.user_prompt,
        tool_name=body.tool_name,
        tool_args=body.tool_args,
        metadata=body.metadata,
    )
    result = service.check(context)
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
