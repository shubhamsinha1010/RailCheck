from __future__ import annotations

from fastapi import Request

from railcheck.application.gate_service import GateService
from railcheck.application.review_service import ReviewService
from railcheck.config import Settings
from railcheck.ports.audit_repository import AuditRepository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_gate_service(request: Request) -> GateService:
    return request.app.state.gate_service


def get_audit_repository(request: Request) -> AuditRepository:
    return request.app.state.audit_repository


def get_review_service(request: Request) -> ReviewService:
    return request.app.state.review_service
