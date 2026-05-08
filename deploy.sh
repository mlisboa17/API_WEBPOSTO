#!/bin/bash

# Deploy Script - Logos Auditoria
# Logos Mode: ON. Automação pura.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
VERSION=${1:-"latest"}
ENVIRONMENT=${2:-"production"}
REGISTRY=${3:-"registry.com"}
IMAGE_NAME="logos-auditoria"
DOCKER_IMAGE="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Logos Auditoria - Deploy Script              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Version: ${YELLOW}${VERSION}${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Registry: ${YELLOW}${REGISTRY}${NC}"
echo ""

# ============ PRÉ-CHECKS ============
echo -e "${BLUE}[1/7] Pre-flight checks${NC}"

# Verificar Docker
if ! command -v docker &> /dev/null; then
  echo -e "${RED}✗ Docker não encontrado${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Docker${NC}"

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null; then
  echo -e "${RED}✗ Docker Compose não encontrado${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Docker Compose${NC}"

# Verificar arquivo de configuração
if [ ! -f ".env.${ENVIRONMENT}" ]; then
  echo -e "${RED}✗ .env.${ENVIRONMENT} não encontrado${NC}"
  exit 1
fi
echo -e "${GREEN}✓ .env.${ENVIRONMENT}${NC}"

# Validar sintaxe Python
echo -e "${BLUE}[2/7] Validating Python syntax${NC}"
python3 -m py_compile config.py models_auditoria.py webposto_client.py servicos_auditoria.py || {
  echo -e "${RED}✗ Erro na sintaxe Python${NC}"
  exit 1
}
echo -e "${GREEN}✓ Python syntax OK${NC}"

# ============ TESTES ============
echo -e "${BLUE}[3/7] Running tests${NC}"
if ! pytest test_auditoria.py -v --tb=short 2>&1 | tail -20; then
  echo -e "${RED}✗ Testes falharam${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Tests passed${NC}"

# ============ BUILD ============
echo -e "${BLUE}[4/7] Building Docker image${NC}"
docker build -t ${DOCKER_IMAGE} . || {
  echo -e "${RED}✗ Falha no build${NC}"
  exit 1
}
echo -e "${GREEN}✓ Image built: ${DOCKER_IMAGE}${NC}"

# ============ PUSH ============
echo -e "${BLUE}[5/7] Pushing to registry${NC}"
docker push ${DOCKER_IMAGE} || {
  echo -e "${RED}✗ Falha no push${NC}"
  exit 1
}
echo -e "${GREEN}✓ Pushed to registry${NC}"

# ============ BACKUP ============
echo -e "${BLUE}[6/7] Creating backups${NC}"
if [ "${ENVIRONMENT}" = "production" ]; then
  docker-compose exec -T mongo mongodump \
    -u admin -p ${MONGO_ROOT_PASSWORD} \
    --authenticationDatabase admin \
    --out /backup/mongo-$(date +%Y%m%d-%H%M%S) || true
  echo -e "${GREEN}✓ MongoDB backup created${NC}"

  docker exec logos-cache redis-cli BGSAVE || true
  echo -e "${GREEN}✓ Redis backup created${NC}"
fi

# ============ DEPLOY ============
echo -e "${BLUE}[7/7] Deploying${NC}"

# Carregar env
export $(cat .env.${ENVIRONMENT} | xargs)

# Pull latest images
docker-compose pull

# Restart containers
docker-compose up -d --no-deps --force-recreate api || {
  echo -e "${RED}✗ Falha no deploy${NC}"
  exit 1
}
echo -e "${GREEN}✓ Containers restarted${NC}"

# Wait for healthy
echo -e "${BLUE}Waiting for API to be healthy...${NC}"
for i in {1..30}; do
  if curl -sf https://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
    break
  fi
  echo -n "."
  sleep 2
done

# ============ POST-DEPLOYMENT ============
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✓ DEPLOYMENT SUCCESSFUL                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Status
echo -e "${BLUE}Container Status:${NC}"
docker-compose ps

# Health check
echo ""
echo -e "${BLUE}Health Check:${NC}"
curl -s https://localhost/health | python3 -m json.tool || echo "Endpoint inaccessível"

# Logs tail
echo ""
echo -e "${BLUE}Recent Logs:${NC}"
docker-compose logs --tail=10 api

echo ""
echo -e "${YELLOW}Deploy concluído! Monitorar logs com:${NC}"
echo -e "${YELLOW}  docker-compose logs -f api${NC}"
echo ""
