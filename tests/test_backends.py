from __future__ import annotations

import httpx
import pytest

from railcheck.adapters.backends.factory import DecisionEngineFactory
from railcheck.adapters.backends.fake import FakeDecisionEngine
from railcheck.adapters.backends.jev import JevDecisionEngine
from railcheck.config import Settings
from railcheck.domain.enums import QuestionType
from railcheck.domain.models import GateContext, QuestionSpec


def test_factory_creates_fake() -> None:
    engine = DecisionEngineFactory.create(Settings(backend="fake"))
    assert isinstance(engine, FakeDecisionEngine)


def test_factory_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        DecisionEngineFactory.create(Settings(backend="nope"))


def test_jev_adapter_parses_systemone_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={"answers": {"contains_pii": {"noul": 0.12, "confidence": 0.9}}},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://api.typesafe.ai")
    engine = JevDecisionEngine(api_key="test-key", client=client)
    answers = engine.evaluate(
        GateContext(candidate_output="hello"),
        [
            QuestionSpec(
                key="contains_pii",
                type=QuestionType.NOUL,
                instructions="Contains PII?",
            )
        ],
    )
    assert answers[0].value == pytest.approx(0.12)
    assert answers[0].confidence == pytest.approx(0.9)
    engine.close()
