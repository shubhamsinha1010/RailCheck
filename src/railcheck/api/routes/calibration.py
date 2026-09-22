from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from railcheck.api.deps import get_calibration_service
from railcheck.api.schemas_calibration import (
    CalibrationReportOut,
    OutcomeCreateRequest,
    OutcomeOut,
    ReliabilityBinOut,
)
from railcheck.application.calibration_service import (
    AuditMissingError,
    CalibrationService,
)

router = APIRouter(tags=["calibration"])


@router.post("/v1/outcomes", response_model=OutcomeOut, status_code=status.HTTP_201_CREATED)
def create_outcome(
    body: OutcomeCreateRequest,
    service: Annotated[CalibrationService, Depends(get_calibration_service)],
) -> OutcomeOut:
    try:
        request_id = UUID(body.request_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="request_id must be a UUID",
        ) from exc
    try:
        record = service.record(
            request_id=request_id,
            field_key=body.field_key,
            label=body.label,
            labeled_by=body.labeled_by,
            note=body.note,
        )
    except AuditMissingError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OutcomeOut(
        id=str(record.id),
        request_id=str(record.request_id),
        field_key=record.field_key,
        label=record.label,
        labeled_by=record.labeled_by,
        labeled_at=record.labeled_at.isoformat(),
        note=record.note,
    )


@router.get("/v1/calibration", response_model=CalibrationReportOut)
def get_calibration(
    service: Annotated[CalibrationService, Depends(get_calibration_service)],
    field: Annotated[str, Query(min_length=1, description="Answer key or gate_action")],
    bins: Annotated[int, Query(ge=2, le=50)] = 10,
) -> CalibrationReportOut:
    report = service.report(field, n_bins=bins)
    return CalibrationReportOut(
        field_key=field,
        n=report.n,
        ece=report.ece,
        brier=report.brier,
        reliability=[
            ReliabilityBinOut(
                lower=b.lower,
                upper=b.upper,
                count=b.count,
                avg_confidence=b.avg_confidence,
                accuracy=b.accuracy,
            )
            for b in report.reliability
        ],
    )
