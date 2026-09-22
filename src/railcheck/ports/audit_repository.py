from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from railcheck.domain.models import AuditRecord


@runtime_checkable
class AuditRepository(Protocol):
    """Port for persisting gate decisions for review and calibration."""

    def save(self, record: AuditRecord) -> None: ...

    def get(self, request_id: UUID) -> AuditRecord | None: ...

    def list_recent(self, limit: int = 50) -> list[AuditRecord]: ...
