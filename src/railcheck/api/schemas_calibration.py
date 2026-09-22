from __future__ import annotations

from pydantic import BaseModel, Field


class OutcomeCreateRequest(BaseModel):
    request_id: str
    field_key: str = Field(..., min_length=1, max_length=128)
    label: str = Field(..., min_length=1, max_length=256)
    labeled_by: str = Field(..., min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=2000)


class OutcomeOut(BaseModel):
    id: str
    request_id: str
    field_key: str
    label: str
    labeled_by: str
    labeled_at: str
    note: str | None = None


class ReliabilityBinOut(BaseModel):
    lower: float
    upper: float
    count: int
    avg_confidence: float
    accuracy: float


class CalibrationReportOut(BaseModel):
    field_key: str
    n: int
    ece: float
    brier: float
    reliability: list[ReliabilityBinOut]
