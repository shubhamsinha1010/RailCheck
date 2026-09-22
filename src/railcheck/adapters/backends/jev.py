from __future__ import annotations

from typing import Any

import httpx

from railcheck.domain.enums import QuestionType
from railcheck.domain.models import Answer, GateContext, QuestionSpec


class JevDecisionEngine:
    """
    Adapter for TypeSafe Jev (hosted System One API).

    Uses the HTTP shape compatible with Jev / laya-serve so the same client can
    target cloud Jev or a local Jev-compatible server.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.typesafe.ai",
        model: str = "jev-latest",
        timeout_s: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Jev backend requires an API key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_s)

    @property
    def name(self) -> str:
        return f"jev:{self._model}"

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def evaluate(self, context: GateContext, questions: list[QuestionSpec]) -> list[Answer]:
        payload = {
            "model": self._model,
            "state": context.as_state(),
            "questions": {q.key: self._to_jev_question(q) for q in questions},
        }
        response = self._client.post(
            f"{self._base_url}/v1/systemone",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        answers_raw = data.get("answers", {})
        return [self._from_jev_answer(q, answers_raw[q.key]) for q in questions]

    @staticmethod
    def _to_jev_question(question: QuestionSpec) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": question.type.value,
            "instructions": question.instructions,
        }
        if question.criteria is not None:
            body["criteria"] = question.criteria
        return body

    @staticmethod
    def _from_jev_answer(question: QuestionSpec, raw: dict[str, Any]) -> Answer:
        if question.type == QuestionType.CHOICE:
            value = raw.get("choice", raw.get("value"))
            probabilities = raw.get("probabilities")
        elif question.type == QuestionType.SCORE:
            value = float(raw.get("score", raw.get("value", 0.0)))
            probabilities = raw.get("probabilities")
        else:
            value = float(raw.get("noul", raw.get("value", 0.0)))
            probabilities = None
        return Answer(
            key=question.key,
            type=question.type,
            value=value,
            confidence=float(raw.get("confidence", 0.0)),
            probabilities=probabilities,
        )
