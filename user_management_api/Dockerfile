FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

ENV POETRY_VIRTUALENVS_CREATE=false

RUN poetry install --no-interaction --no-root --without dev

COPY . .

FROM python:3.13-slim AS production

WORKDIR /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

EXPOSE 8000

CMD ["uvicorn", "src.user_management_api.main:app", "--host", "0.0.0.0", "--port", "8000"]