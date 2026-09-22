from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from railcheck.domain.models import OutcomeRecord


@runtime_checkable
class OutcomeRepository(Protocol):
    """Port for ground-truth labels used by calibration."""

    def save(self, record: OutcomeRecord) -> None: ...

    def list_for_field(self, field_key: str) -> list[OutcomeRecord]: ...

    def get_for_request(self, request_id: UUID) -> list[OutcomeRecord]: ...
