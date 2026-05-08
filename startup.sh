#!/bin/bash

# Script de startup para Logos Auditoria
# Logos Mode: ON. Sem explicações longas.

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════╗"
echo "║     Logos Auditoria - Startup Script             ║"
echo "╚═══════════════════════════════════════════════════╝"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Validar .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env não encontrado${NC}"
    echo "Copiando .env.example → .env"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  EDITAR .env com credenciais reais!${NC}"
else
    echo -e "${GREEN}✓ .env encontrado${NC}"
fi

# 2. Validar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 não encontrado${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $(python3 --version)${NC}"

# 3. Instalar dependências
echo ""
echo "Instalando dependências..."
pip install -r requirements.txt --break-system-packages > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependências instaladas${NC}"
else
    echo -e "${RED}✗ Erro ao instalar dependências${NC}"
    exit 1
fi

# 4. Validar arquivos
echo ""
echo "Validando arquivos..."
FILES=(
    "config.py"
    "models_auditoria.py"
    "webposto_client.py"
    "servicos_auditoria.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file não encontrado${NC}"
        exit 1
    fi
done

# 5. Health check de configuração
echo ""
echo "Validando configurações..."
python3 -c "
from config import initialize_config
if initialize_config():
    exit(0)
else:
    exit(1)
" || {
    echo -e "${YELLOW}⚠️  Config com warnings - continuando...${NC}"
}

# 6. Info final
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Startup OK. Pronto para rodar!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Editar .env com credenciais reais"
echo "  2. python servicos_auditoria.py"
echo "  3. curl http://localhost:8000/auditoria/health"
echo ""
echo "Documentação:"
echo "  • AUDITORIA_README.md - Estrutura de dados"
echo "  • INTEGRACAO_WEBPOSTO.md - Setup webPosto"
echo ""
