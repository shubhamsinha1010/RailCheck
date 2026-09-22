from __future__ import annotations

import re

from railcheck.domain.enums import QuestionType
from railcheck.domain.models import Answer, GateContext, QuestionSpec


class FakeDecisionEngine:
    """
    Deterministic, dependency-free backend for tests and local demos.

    Heuristics are intentionally simple — production accuracy comes from Laya/Jev.
    """

    _EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    _PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    _JAILBREAK = re.compile(
        r"ignore (all |previous )?instructions|jailbreak|dan mode|developer mode",
        re.I,
    )
    _POLICY = re.compile(
        r"\b(how to make a bomb|steal credit card|ransomware|child sexual)\b",
        re.I,
    )

    @property
    def name(self) -> str:
        return "fake"

    def evaluate(self, context: GateContext, questions: list[QuestionSpec]) -> list[Answer]:
        text = context.as_state()
        prompt = context.user_prompt or ""
        combined = f"{prompt}\n{text}"

        contains_pii = bool(self._EMAIL.search(text) or self._PHONE.search(text))
        jailbreak = bool(self._JAILBREAK.search(combined))
        policy_hit = bool(self._POLICY.search(text))
        tool_abuse = bool(
            context.tool_name
            and any(
                token in (context.tool_name or "").lower()
                for token in ("shell", "exec", "rm", "delete_all")
            )
        )

        if jailbreak or policy_hit or tool_abuse:
            risk, harm = "block", 3.0
        elif contains_pii:
            risk, harm = "rewrite", 1.0
        else:
            risk, harm = "allow", 0.0

        signals = {
            "risk_class": (risk, 0.92 if risk != "allow" else 0.9),
            "harm_severity": (harm, 0.9),
            "contains_pii": (1.0 if contains_pii else 0.05, 0.88 if contains_pii else 0.9),
            "jailbreak_success": (0.95 if jailbreak else 0.05, 0.9),
            "policy_violation": (0.95 if policy_hit else 0.05, 0.9),
            "tool_abuse": (0.95 if tool_abuse else 0.05, 0.9),
        }

        answers: list[Answer] = []
        for question in questions:
            value, confidence = signals.get(question.key, self._default_for(question))
            probabilities = None
            if question.type == QuestionType.CHOICE and isinstance(question.criteria, dict):
                other = (1.0 - confidence) / max(len(question.criteria) - 1, 1)
                probabilities = {
                    label: confidence if label == value else other for label in question.criteria
                }
            answers.append(
                Answer(
                    key=question.key,
                    type=question.type,
                    value=value,
                    confidence=confidence,
                    probabilities=probabilities,
                )
            )
        return answers

    @staticmethod
    def _default_for(question: QuestionSpec) -> tuple[object, float]:
        if question.type == QuestionType.CHOICE and isinstance(question.criteria, dict):
            return next(iter(question.criteria)), 0.55
        if question.type == QuestionType.SCORE:
            return 0.0, 0.55
        return 0.1, 0.55
