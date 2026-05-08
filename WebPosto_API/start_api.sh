#!/bin/bash

# Script para iniciar a API webPosto Sync Service
# Uso: ./start_api.sh [dev|prod]

MODE="${1:-dev}"
POETRY_PATH="/sessions/gallant-zealous-bohr/.local/bin/poetry"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

echo "🚀 Iniciando webPosto API em modo: $MODE"
echo "📍 Diretório: $PROJECT_DIR"
echo "🔑 Chave de API: ${WEBPOSTO_API_KEY:0:8}***"

if [ "$MODE" = "dev" ]; then
    echo "📍 Modo desenvolvimento (com auto-reload)"
    $POETRY_PATH run uvicorn src.main_minimal:app --host 0.0.0.0 --port 8000 --reload
else
    echo "📍 Modo produção (4 workers)"
    $POETRY_PATH run uvicorn src.main_minimal:app --host 0.0.0.0 --port 8000 --workers 4
fi
