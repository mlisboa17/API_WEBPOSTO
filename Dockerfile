# Dockerfile - Logos Auditoria
# Multi-stage build para produção otimizada

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Criar user não-root por segurança
RUN groupadd -r logos && useradd -r -g logos logos

# Copiar Python packages do builder
COPY --from=builder /root/.local /home/logos/.local

# Copiar código
COPY config.py .
COPY models.py .
COPY models_auditoria.py .
COPY webposto_client.py .
COPY servicos_auditoria.py .

# Variáveis de ambiente
ENV PATH=/home/logos/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/auditoria/health', timeout=5).read()" || exit 1

# User
USER logos

# Expose
EXPOSE 8000

# Entrypoint
CMD ["python", "-m", "uvicorn", "servicos_auditoria:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log"]
