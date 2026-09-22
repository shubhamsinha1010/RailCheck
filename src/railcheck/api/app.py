from __future__ import annotations

from fastapi import FastAPI

from railcheck.adapters.backends.factory import DecisionEngineFactory
from railcheck.adapters.persistence.memory_audit import InMemoryAuditRepository
from railcheck.api.routes import gate, health
from railcheck.application.gate_service import GateService
from railcheck.config import Settings
from railcheck.packs.safety import SafetyPack
from railcheck.policy.bands import ConfidenceBands
from railcheck.policy.engine import PolicyEngine


def create_app(settings: Settings | None = None) -> FastAPI:
    """Composition root: wire ports to adapters once at startup."""
    settings = settings or Settings()
    engine = DecisionEngineFactory.create(settings)
    audit = InMemoryAuditRepository()
    policy = PolicyEngine(
        ConfidenceBands(
            allow_min_confidence=settings.allow_threshold,
            block_min_confidence=settings.block_threshold,
            noul_positive_threshold=settings.noul_positive_threshold,
            harm_block_score=settings.harm_block_score,
        )
    )
    gate_service = GateService(
        engine=engine,
        policy=policy,
        pack=SafetyPack(),
        audit=audit,
    )

    app = FastAPI(
        title="RailCheck",
        description="Calibrated safety gate for LLM and agent outputs",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.gate_service = gate_service
    app.state.audit_repository = audit

    app.include_router(health.router)
    app.include_router(gate.router)
    return app


def run() -> None:
    import uvicorn

    settings = Settings()
    uvicorn.run(
        "railcheck.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )
