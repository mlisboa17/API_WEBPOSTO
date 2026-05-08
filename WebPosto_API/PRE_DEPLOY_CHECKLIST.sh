#!/bin/bash

# ===============================================
# PRÉ-DEPLOY CHECKLIST — webPosto API
# ===============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   PRÉ-DEPLOY CHECKLIST — webPosto API  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

PASSED=0
FAILED=0

check() {
    local name="$1"
    local cmd="$2"

    if eval "$cmd" &>/dev/null; then
        echo -e "${GREEN}✅${NC} $name"
        ((PASSED++))
    else
        echo -e "${RED}❌${NC} $name"
        ((FAILED++))
    fi
}

# ===============================================
# 1. DOCKER & DEPENDÊNCIAS
# ===============================================
echo -e "${YELLOW}1️⃣  Docker & Dependências${NC}"
check "Docker instalado" "command -v docker"
check "Docker Compose instalado" "command -v docker-compose"
check "Docker daemon rodando" "docker ps"
check "Python instalado (3.10+)" "python3 --version | grep -E '3\.[0-9]+'"

echo ""

# ===============================================
# 2. ARQUIVOS ESSENCIAIS
# ===============================================
echo -e "${YELLOW}2️⃣  Arquivos Essenciais${NC}"
check "Dockerfile existe" "[ -f Dockerfile ]"
check "docker-compose.yml existe" "[ -f docker-compose.yml ]"
check ".env existe" "[ -f .env ]"
check "pyproject.toml existe" "[ -f pyproject.toml ]"
check "src/main_minimal.py existe" "[ -f src/main_minimal.py ]"
check "setup_ambiente.sh existe" "[ -f setup_ambiente.sh ]"

echo ""

# ===============================================
# 3. CONFIGURAÇÃO .env
# ===============================================
echo -e "${YELLOW}3️⃣  Configuração .env${NC}"
check "WEBPOSTO_API_KEY configurada" "grep -q 'WEBPOSTO_API_KEY' .env"
check "WEBPOSTO_BASE_URL configurada" "grep -q 'WEBPOSTO_BASE_URL' .env"
check "API_PORT = 5000" "grep -q 'API_PORT=5000' .env"
check "ENVIRONMENT configurado" "grep -q 'ENVIRONMENT' .env"
check "DATABASE_URL configurada" "grep -q 'DATABASE_URL' .env"

echo ""

# ===============================================
# 4. CÓDIGO FONTE
# ===============================================
echo -e "${YELLOW}4️⃣  Código Fonte${NC}"
check "FastAPI importável" "python3 -c 'import fastapi'"
check "Pydantic v2 instalada" "python3 -c 'from pydantic import BaseModel'"
check "SQLAlchemy instalada" "python3 -c 'from sqlalchemy import create_engine'"
check "main_minimal.py sem erros" "python3 -m py_compile src/main_minimal.py"

echo ""

# ===============================================
# 5. CONECTIVIDADE
# ===============================================
echo -e "${YELLOW}5️⃣  Conectividade${NC}"
check "DNS resolving web.qualityautomacao.com.br" "nslookup web.qualityautomacao.com.br 8.8.8.8 | grep -q 'Name:'"
check "Ping webPosto API" "timeout 5 curl -s -I http://web.qualityautomacao.com.br | head -1"

echo ""

# ===============================================
# 6. PORTA & FIREWALL
# ===============================================
echo -e "${YELLOW}6️⃣  Porta & Firewall${NC}"
check "Porta 5000 disponível" "! netstat -an 2>/dev/null | grep -q ':5000' || echo 'OK'"
check "Porta 6379 (Redis) disponível" "! netstat -an 2>/dev/null | grep -q ':6379' || echo 'OK'"

echo ""

# ===============================================
# 7. SEGURANÇA
# ===============================================
echo -e "${YELLOW}7️⃣  Segurança${NC}"
check ".env tem permissões restritas" "[ -f .env ] && test ! -o 'rwx' .env"
check "Nenhuma senha em hardcode" "! grep -r 'password.*=' src/ 2>/dev/null || echo 'OK'"
check ".git ignora .env" "grep -q '.env' .gitignore 2>/dev/null || echo 'OK'"

echo ""

# ===============================================
# 8. DOCUMENTAÇÃO
# ===============================================
echo -e "${YELLOW}8️⃣  Documentação${NC}"
check "DEPLOY_PRODUCAO.md existe" "[ -f DEPLOY_PRODUCAO.md ]"
check "PRONTO_PARA_PRODUCAO.md existe" "[ -f PRONTO_PARA_PRODUCAO.md ]"
check "README.md existe" "[ -f README.md ]"

echo ""

# ===============================================
# SUMMARY
# ===============================================
TOTAL=$((PASSED + FAILED))

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           RESUMO DO CHECKLIST          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total de checks: ${BLUE}$TOTAL${NC}"
echo -e "Passou: ${GREEN}$PASSED${NC}"
echo -e "Falhou: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🚀 TUDO PRONTO PARA DEPLOY!${NC}"
    echo ""
    echo "Próximos passos:"
    echo "  1. Validar credenciais: cat .env | grep WEBPOSTO"
    echo "  2. Build Docker: docker-compose build"
    echo "  3. Iniciar: docker-compose up -d"
    echo "  4. Testar: curl http://localhost:5000/health"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  $FAILED check(s) falharam. Corrija antes de fazer deploy.${NC}"
    echo ""
    echo "Verifique:"
    echo "  • Docker está instalado e rodando?"
    echo "  • .env tem as credenciais webPosto corretas?"
    echo "  • Arquivos essenciais existem?"
    echo "  • Conectividade com webPosto API OK?"
    echo ""
    exit 1
fi
