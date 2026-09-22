from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from railcheck.domain.enums import GateAction, ReviewResolution, ReviewStatus


class ResolveReviewRequest(BaseModel):
    resolution: ReviewResolution
    resolver: str = Field(..., min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=2000)
    rewritten_output: str | None = None

    @model_validator(mode="after")
    def rewrite_requires_output(self) -> ResolveReviewRequest:
        if self.resolution is ReviewResolution.REWRITE and not self.rewritten_output:
            raise ValueError("rewritten_output is required when resolution is rewrite")
        return self


class ReviewItemOut(BaseModel):
    id: str
    status: ReviewStatus
    action: GateAction
    reason: str
    triggered_by: str | None
    pack: str
    backend: str
    candidate_output: str
    user_prompt: str | None
    tool_name: str | None
    answers: list[dict[str, Any]]
    created_at: datetime
    resolved_at: datetime | None = None
    resolver: str | None = None
    resolution: ReviewResolution | None = None
    note: str | None = None
    rewritten_output: str | None = None


class ReviewListOut(BaseModel):
    items: list[ReviewItemOut]
    count: int
