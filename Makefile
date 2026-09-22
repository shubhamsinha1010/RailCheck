.PHONY: install test lint run compose-up compose-down

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src tests

run:
	uvicorn railcheck.api.app:create_app --factory --host 0.0.0.0 --port 8080 --reload

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down
