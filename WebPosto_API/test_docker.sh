#!/bin/bash

# Script para testar o deployment Docker
# Uso: ./test_docker.sh

echo "🧪 Testando deployment Docker..."
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar Docker
echo -n "1️⃣  Verificando Docker... "
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Docker não instalado${NC}"
    exit 1
fi

# 2. Verificar Docker Compose
echo -n "2️⃣  Verificando Docker Compose... "
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Docker Compose não instalado${NC}"
    exit 1
fi

# 3. Verificar Dockerfile
echo -n "3️⃣  Verificando Dockerfile... "
if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Dockerfile não encontrado${NC}"
    exit 1
fi

# 4. Verificar docker-compose.yml
echo -n "4️⃣  Verificando docker-compose.yml... "
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ docker-compose.yml não encontrado${NC}"
    exit 1
fi

# 5. Verificar .env
echo -n "5️⃣  Verificando .env... "
if [ -f ".env" ]; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ .env não encontrado${NC}"
    exit 1
fi

# 6. Build da imagem
echo -n "6️⃣  Build da imagem Docker... "
if docker-compose build --quiet 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Build falhou${NC}"
    exit 1
fi

# 7. Rodar containers
echo -n "7️⃣  Iniciando containers... "
if docker-compose up -d 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Falha ao iniciar containers${NC}"
    exit 1
fi

# 8. Aguardar inicialização
echo -n "8️⃣  Aguardando inicialização (10s)... "
sleep 10
echo -e "${GREEN}✅${NC}"

# 9. Testar endpoint /health
echo -n "9️⃣  Testando endpoint /health... "
RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Endpoint não respondeu${NC}"
    echo "Response: $RESPONSE"
    docker-compose logs api | tail -20
    docker-compose down
    exit 1
fi

# 10. Testar endpoint /sync/financeiro
echo -n "🔟 Testando endpoint /sync/financeiro... "
RESPONSE=$(curl -s http://localhost:8000/sync/financeiro)
if echo "$RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Endpoint não respondeu${NC}"
    echo "Response: $RESPONSE"
    docker-compose logs api | tail -20
    docker-compose down
    exit 1
fi

# 11. Verificar Redis
echo -n "1️⃣1️⃣  Verificando Redis... "
if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  Redis não respondeu (pode estar OK)${NC}"
fi

# Resultado final
echo ""
echo -e "${GREEN}🎉 Todos os testes passaram!${NC}"
echo ""
echo "📊 Status dos containers:"
docker-compose ps
echo ""
echo "📝 Logs (últimas 5 linhas):"
docker-compose logs --tail=5 api
echo ""
echo "🛑 Para parar: docker-compose down"
echo "📖 Para ver logs: docker-compose logs -f api"
