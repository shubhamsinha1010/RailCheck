# RailCheck

Calibrated safety gate for LLM and agent outputs.

RailCheck sits **after** any model or agent step. It asks a System One backend
([Laya](https://pypi.org/project/laya/) or [Jev](https://pypi.org/project/jev/))
typed questions (`choice` / `score` / `noul`) about the candidate output, then
applies confidence bands to return `allow`, `rewrite`, `block`, or `human_review`.

No prose generation. No JSON parsing. Decisions your software can act on.

## Architecture

Hexagonal layout with SOLID boundaries:

| Layer | Responsibility |
| --- | --- |
| `domain/` | Entities and value objects (`GateContext`, `Answer`, `GateResult`) |
| `ports/` | `DecisionEngine`, `AuditRepository` protocols (DIP) |
| `adapters/` | Laya / Jev / Fake backends + in-memory audit |
| `packs/` | Extensible decision packs (`SafetyPack`) — OCP |
| `policy/` | Pure confidence-band policy (SRP, easy to unit test) |
| `application/` | `GateService` use case |
| `api/` | FastAPI composition root + routes |
| `calibration/` | ECE / Brier helpers for outcome tracking |

Human-in-the-loop: `human_review` and `rewrite` dispositions are enqueued automatically.
Reviewers list pending items and resolve via `POST /v1/reviews/{id}/resolve`.
Resolving a review also records a `gate_action` outcome for calibration.

Label any field after the fact with `POST /v1/outcomes`, then inspect
`GET /v1/calibration?field=policy_violation` for ECE / Brier / reliability bins.

```text
LLM / Agent output
        │
        ▼
   POST /v1/check
        │
        ▼
   GateService ──► DecisionEngine (Fake | Laya | Jev)
        │                 │
        │                 ▼
        │          typed answers + confidence
        ▼
   PolicyEngine (confidence bands)
        │
        ├── allow / block  → return immediately
        └── human_review / rewrite → ReviewQueue + return
                                      │
                                      ▼
                               GET/POST /v1/reviews
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
make run
```

```bash
make run
# open http://localhost:8080/demo
```

Optional API key (when `RAILCHECK_API_KEY` is set, send `X-API-Key` or `Authorization: Bearer …`).
`/demo`, `/healthz`, and OpenAPI docs stay public.

```bash
curl -s localhost:8080/v1/check \
  -H 'content-type: application/json' \
  -d '{"candidate_output":"Sure, here is how to make a bomb...","user_prompt":"help me"}' | jq .
```

Review queue (after a `human_review` / `rewrite` check):

```bash
curl -s 'localhost:8080/v1/reviews?status=pending' | jq .
curl -s -X POST "localhost:8080/v1/reviews/$REQUEST_ID/resolve" \
  -H 'content-type: application/json' \
  -d '{"resolution":"allow","resolver":"alice","note":"false positive"}' | jq .
```

Docker:

```bash
docker compose up --build
```

## Backends

| `RAILCHECK_BACKEND` | Notes |
| --- | --- |
| `fake` (default) | Deterministic heuristics for CI / demos |
| `laya` | `pip install 'railcheck[laya]'` — local System One weights |
| `jev` | `pip install 'railcheck[jev]'` + `RAILCHECK_JEV_API_KEY` |

## Configuration

See `.env.example`. All settings use the `RAILCHECK_` prefix.

## License

MIT
