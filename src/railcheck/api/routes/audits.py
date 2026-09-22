from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from railcheck.api.deps import get_audit_repository
from railcheck.api.schemas import AnswerOut, GateCheckResponse
from railcheck.domain.models import AuditRecord
from railcheck.ports.audit_repository import AuditRepository

router = APIRouter(prefix="/v1/audits", tags=["audits"])


def _to_out(record: AuditRecord) -> GateCheckResponse:
    result = record.result
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


@router.get("", response_model=list[GateCheckResponse])
def list_audits(
    audits: Annotated[AuditRepository, Depends(get_audit_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[GateCheckResponse]:
    return [_to_out(r) for r in audits.list_recent(limit=limit)]


@router.get("/{request_id}", response_model=GateCheckResponse)
def get_audit(
    request_id: UUID,
    audits: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> GateCheckResponse:
    record = audits.get(request_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return _to_out(record)
