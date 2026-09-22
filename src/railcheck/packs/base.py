from __future__ import annotations

from abc import ABC, abstractmethod

from railcheck.domain.models import QuestionSpec


class DecisionPack(ABC):
    """Open/Closed: new safety packs extend this without changing the gate service."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def questions(self) -> list[QuestionSpec]:
        """Typed questions evaluated in a single System One forward pass."""
        ...
