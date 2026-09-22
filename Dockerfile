FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RAILCHECK_BACKEND=fake

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD ["uvicorn", "railcheck.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
