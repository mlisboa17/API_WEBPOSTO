#!/bin/bash
# Logos WebPosto Gateway - Quick Start Script

echo "🚀 Logos Gateway API - Setup Rápido"
echo "===================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.12+."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Criar venv
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar venv
echo "🔌 Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo "📚 Instalando dependências..."
pip install -r requirements.txt

# Copiar .env
if [ ! -f ".env" ]; then
    echo "📝 Copiando .env.example para .env..."
    cp .env.example .env
fi

echo ""
echo "✅ Setup completo!"
echo ""
echo "Próximos passos:"
echo "  1. docker compose up -d          # Inicia API + Valkey"
echo "  2. curl http://localhost:8050/ready   # Testa endpoint"
echo "  3. pytest tests/ -v              # Roda testes"
echo ""
