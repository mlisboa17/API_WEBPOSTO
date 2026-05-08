#!/bin/bash

# ============================================
# Setup Automático — webPosto API + Confluence
# ============================================

set -e

echo "🚀 Setup webPosto API + Confluence Integration"
echo "=============================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Verificar Docker
echo -n "1️⃣  Verificando Docker... "
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não instalado${NC}"
    echo "Instale: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
echo -e "${GREEN}✅${NC}"

# 2. Verificar Docker Compose
echo -n "2️⃣  Verificando Docker Compose... "
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não instalado${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC}"

# 3. Criar diretório do projeto
PROJETO_DIR="/opt/webposto-api"
echo -n "3️⃣  Preparando diretório ($PROJETO_DIR)... "
mkdir -p "$PROJETO_DIR"
echo -e "${GREEN}✅${NC}"

# 4. Copiar arquivos
echo -n "4️⃣  Copiando arquivos do projeto... "
cp -r . "$PROJETO_DIR/" 2>/dev/null || true
echo -e "${GREEN}✅${NC}"

# 5. Validar arquivos críticos
echo "5️⃣  Validando arquivos críticos..."
ARQUIVOS=("Dockerfile" "docker-compose.yml" ".env" "src/main_minimal.py")
for arquivo in "${ARQUIVOS[@]}"; do
    if [ -f "$PROJETO_DIR/$arquivo" ]; then
        echo -e "   ${GREEN}✅${NC} $arquivo"
    else
        echo -e "   ${RED}❌${NC} $arquivo (FALTANDO)"
    fi
done

# 6. Build das imagens
echo ""
echo -n "6️⃣  Build das imagens Docker (pode demorar ~2min)... "
cd "$PROJETO_DIR"
docker-compose build --quiet 2>/dev/null
echo -e "${GREEN}✅${NC}"

# 7. Rodar containers
echo -n "7️⃣  Iniciando containers... "
docker-compose up -d 2>/dev/null
echo -e "${GREEN}✅${NC}"

# 8. Aguardar inicialização
echo "8️⃣  Aguardando inicialização (10 segundos)..."
sleep 10

# 9. Testar health
echo -n "9️⃣  Testando API (/health)... "
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  Resposta inesperada${NC}"
    echo "   Verifique logs: docker-compose logs api"
fi

# 10. Status final
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup completo!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

echo "📊 Status dos containers:"
docker-compose ps
echo ""

echo "📡 Endpoints disponíveis:"
echo -e "   ${BLUE}http://localhost:5000/health${NC}            - Health check"
echo -e "   ${BLUE}http://localhost:5000/sync/financeiro${NC}  - Financeiro"
echo -e "   ${BLUE}http://localhost:5000/sync/caixa${NC}       - Caixa"
echo ""

echo "🔗 Integração Confluence:"
echo -e "   ${YELLOW}API URL: http://localhost:5000${NC}"
echo -e "   ${YELLOW}Plugin: confluence-plugin-webposto.py${NC}"
echo ""

echo "📝 Próximos passos:"
echo "   1. Testar: curl http://localhost:5000/health"
echo "   2. Instalar plugin em Confluence"
echo "   3. Configurar URL da API: http://localhost:5000"
echo ""

echo "🛑 Comandos úteis:"
echo "   Ver logs:        docker-compose logs -f api"
echo "   Parar:           docker-compose down"
echo "   Reiniciar:       docker-compose restart"
echo ""

# Salvar informações
cat > "$PROJETO_DIR/setup_info.txt" << EOF
webPosto API Setup
==================
Data: $(date)
Diretório: $PROJETO_DIR
Porta: 5000
Status: ✅ Online

URLs:
- API: http://localhost:5000
- Financeiro: http://localhost:5000/sync/financeiro
- Caixa: http://localhost:5000/sync/caixa

Próximos passos:
1. Integrar com Confluence via plugin
2. Configurar sincronização automática
3. Testar endpoints
EOF

echo -e "${GREEN}✅ Informações salvas em: setup_info.txt${NC}"
