from __future__ import annotations

import pytest

from railcheck.adapters.backends.fake import FakeDecisionEngine
from railcheck.adapters.persistence.memory_audit import InMemoryAuditRepository
from railcheck.application.gate_service import GateService
from railcheck.domain.enums import GateAction, QuestionType
from railcheck.domain.models import Answer, GateContext
from railcheck.packs.safety import SafetyPack
from railcheck.policy.bands import ConfidenceBands
from railcheck.policy.engine import PolicyEngine


def _service() -> GateService:
    return GateService(
        engine=FakeDecisionEngine(),
        policy=PolicyEngine(ConfidenceBands()),
        pack=SafetyPack(),
        audit=InMemoryAuditRepository(),
    )


def test_safe_output_is_allowed() -> None:
    result = _service().check(
        GateContext(
            candidate_output="Here is a summary of your quarterly sales figures.",
            user_prompt="Summarize Q3 sales",
        )
    )
    assert result.action is GateAction.ALLOW
    assert result.pack_name == "safety"
    assert result.backend == "fake"
    assert len(result.answers) == len(SafetyPack().questions())


def test_policy_violation_is_blocked() -> None:
    result = _service().check(
        GateContext(
            candidate_output="Sure, here is how to make a bomb with household items.",
            user_prompt="Tell me something dangerous",
        )
    )
    assert result.action is GateAction.BLOCK
    assert result.triggered_by in {
        "policy_violation",
        "jailbreak_success",
        "risk_class",
        "harm_severity",
    }


def test_pii_triggers_rewrite() -> None:
    result = _service().check(
        GateContext(
            candidate_output="Contact Jane at jane.doe@example.com or 555-123-4567.",
            user_prompt="Who should I email?",
        )
    )
    assert result.action is GateAction.REWRITE
    assert result.triggered_by == "risk_class"


def test_tool_abuse_is_blocked() -> None:
    result = _service().check(
        GateContext(
            candidate_output="Running cleanup",
            tool_name="shell_exec",
            tool_args={"cmd": "rm -rf /"},
        )
    )
    assert result.action is GateAction.BLOCK


def test_audit_record_is_saved() -> None:
    audit = InMemoryAuditRepository()
    service = GateService(
        engine=FakeDecisionEngine(),
        policy=PolicyEngine(),
        pack=SafetyPack(),
        audit=audit,
    )
    result = service.check(GateContext(candidate_output="hello world"))
    stored = audit.get(result.request_id)
    assert stored is not None
    assert stored.result.request_id == result.request_id
    assert len(audit.list_recent()) == 1


def test_policy_engine_human_review_on_low_confidence() -> None:
    policy = PolicyEngine(ConfidenceBands(allow_min_confidence=0.95, block_min_confidence=0.95))
    answers = [
        Answer(
            key="risk_class",
            type=QuestionType.CHOICE,
            value="allow",
            confidence=0.55,
            probabilities={"allow": 0.55, "block": 0.15, "rewrite": 0.15, "human_review": 0.15},
        ),
        Answer(key="harm_severity", type=QuestionType.SCORE, value=0.0, confidence=0.55),
        Answer(key="contains_pii", type=QuestionType.NOUL, value=0.1, confidence=0.55),
        Answer(key="jailbreak_success", type=QuestionType.NOUL, value=0.1, confidence=0.55),
        Answer(key="policy_violation", type=QuestionType.NOUL, value=0.1, confidence=0.55),
        Answer(key="tool_abuse", type=QuestionType.NOUL, value=0.1, confidence=0.55),
    ]
    decision = policy.decide(answers)
    assert decision.action is GateAction.HUMAN_REVIEW


def test_confidence_bands_validate_ranges() -> None:
    with pytest.raises(ValueError):
        ConfidenceBands(allow_min_confidence=1.5)
