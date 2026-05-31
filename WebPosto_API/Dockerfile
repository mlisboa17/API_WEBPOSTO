# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir poetry poetry-plugin-export

COPY pyproject.toml poetry.lock* ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes 2>/dev/null \
    || poetry export -f requirements.txt --output requirements.txt --without-hashes --only main

RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.11-slim AS runtime

LABEL maintainer="Grupo Lisboa <mlisboa17@gmail.com>"
LABEL description="Logos WebPosto Gateway — FastAPI + DDD + resiliência"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY src ./src
COPY theme ./theme
COPY static ./static
COPY dashboard_vendas.html api_hub_get_catalog.json api_hub_catalog.js ./

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.presentation.app:app", "--host", "0.0.0.0", "--port", "8000"]
