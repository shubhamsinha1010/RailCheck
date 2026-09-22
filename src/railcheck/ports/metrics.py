from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MetricsCollector(Protocol):
    def inc_gate_check(self, action: str) -> None: ...

    def observe_gate_latency_seconds(self, seconds: float) -> None: ...

    def set_review_pending(self, count: int) -> None: ...

    def render_prometheus(self) -> str: ...
