from __future__ import annotations

from enum import StrEnum


class QuestionType(StrEnum):
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


class GateAction(StrEnum):
    """Disposition returned to the calling application."""

    ALLOW = "allow"
    REWRITE = "rewrite"
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"


class BackendKind(StrEnum):
    FAKE = "fake"
    LAYA = "laya"
    JEV = "jev"
