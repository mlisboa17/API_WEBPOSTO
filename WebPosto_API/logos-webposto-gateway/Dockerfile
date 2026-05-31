# Multi-stage Dockerfile otimizado para Logos Gateway API
# Build de produção: ~100MB (python:3.12-slim base)

FROM python:3.12-slim as builder

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Criar wheelhouse (pre-compiled binaries)
RUN pip install --no-cache-dir wheel && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# =============================================================================
# Production Stage
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8050

# Criar usuário não-root para segurança
RUN useradd -m -u 1000 appuser

# Copiar wheels do builder
COPY --from=builder /app/wheels /app/wheels
COPY --from=builder /app/requirements.txt .

# Instalar dependências do wheels
RUN pip install --no-cache-dir --no-index --find-links /app/wheels -r requirements.txt && \
    rm -rf /app/wheels

# Copiar código da aplicação
COPY . .

# Dar permissões ao usuário
RUN chown -R appuser:appuser /app

# Trocar para usuário não-root
USER appuser

# Expor porta 8050
EXPOSE 8050

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/health')"

# Comando de inicialização
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8050"]

