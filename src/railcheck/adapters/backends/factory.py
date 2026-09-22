from __future__ import annotations

from railcheck.adapters.backends.fake import FakeDecisionEngine
from railcheck.adapters.backends.jev import JevDecisionEngine
from railcheck.adapters.backends.laya import LayaDecisionEngine
from railcheck.config import Settings
from railcheck.domain.enums import BackendKind
from railcheck.ports.decision_engine import DecisionEngine


class DecisionEngineFactory:
    """Factory Method: construct the configured DecisionEngine without coupling callers."""

    @staticmethod
    def create(settings: Settings) -> DecisionEngine:
        kind = BackendKind(settings.backend)
        if kind is BackendKind.FAKE:
            return FakeDecisionEngine()
        if kind is BackendKind.LAYA:
            return LayaDecisionEngine(model_id=settings.laya_model, device=settings.laya_device)
        if kind is BackendKind.JEV:
            return JevDecisionEngine(
                api_key=settings.jev_api_key,
                base_url=settings.jev_base_url,
                model=settings.jev_model,
            )
        raise ValueError(f"Unsupported backend: {settings.backend}")
