from __future__ import annotations

from typing import Protocol, runtime_checkable

from railcheck.domain.models import Answer, GateContext, QuestionSpec


@runtime_checkable
class DecisionEngine(Protocol):
    """Port for System One backends (Laya, Jev, or test doubles)."""

    @property
    def name(self) -> str: ...

    def evaluate(self, context: GateContext, questions: list[QuestionSpec]) -> list[Answer]:
        """Answer all questions against the gate context in one call."""
        ...
