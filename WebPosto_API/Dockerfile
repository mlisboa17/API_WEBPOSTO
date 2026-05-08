FROM python:3.10-slim

# Metadados
LABEL maintainer="Grupo Lisboa <mlisboa17@gmail.com>"
LABEL description="webPosto Sync Service — FastAPI + SQLAlchemy"
LABEL version="0.1.0"

WORKDIR /app

# Instalar Poetry
RUN pip install --no-cache-dir poetry

# Copiar arquivos de dependência
COPY pyproject.toml poetry.lock* ./

# Instalar dependências (sem dev)
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copiar código fonte
COPY src ./src
COPY .env ./.env

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=5 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Expor porta
EXPOSE 5000

# Iniciar API em produção
CMD ["uvicorn", "src.main_minimal:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "4"]
