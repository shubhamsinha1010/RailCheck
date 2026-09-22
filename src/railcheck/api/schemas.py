from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from railcheck.domain.enums import GateAction


class GateCheckRequest(BaseModel):
    candidate_output: str = Field(..., min_length=1)
    user_prompt: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnswerOut(BaseModel):
    key: str
    type: str
    value: Any
    confidence: float
    probabilities: dict[str, float] | None = None


class GateCheckResponse(BaseModel):
    request_id: str
    action: GateAction
    reason: str
    triggered_by: str | None
    pack: str
    backend: str
    answers: list[AnswerOut]
    created_at: str
