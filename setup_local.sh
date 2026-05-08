#!/bin/bash

# Setup Local - Logos Auditoria
# Máquina nova → Desenvolvimento local completo
# Logos Mode: ON

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Logos Auditoria - Setup Local                ║${NC}"
echo -e "${BLUE}║  Máquina Nova → Desenvolvimento               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ============ DETECÇÃO DO SISTEMA ============
echo -e "${BLUE}[1/8] Detectando sistema operacional...${NC}"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    fi
    echo -e "${GREEN}✓ Linux ($DISTRO)${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo -e "${GREEN}✓ macOS${NC}"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    echo -e "${YELLOW}⚠️  Windows (use WSL2 recomendado)${NC}"
else
    echo -e "${RED}✗ Sistema operacional não suportado${NC}"
    exit 1
fi

# ============ INSTALAR DEPENDÊNCIAS DO SISTEMA ============
echo ""
echo -e "${BLUE}[2/8] Instalando dependências do sistema...${NC}"

if [ "$OS" == "linux" ]; then
    if [ "$DISTRO" == "ubuntu" ] || [ "$DISTRO" == "debian" ]; then
        echo "Atualizando repositórios..."
        sudo apt-get update

        echo "Instalando Docker..."
        sudo apt-get install -y docker.io docker-compose-plugin

        echo "Instalando Python 3.11..."
        sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

        echo "Instalando ferramentas..."
        sudo apt-get install -y git curl wget vim nano jq

        # Adicionar user ao grupo docker
        sudo usermod -aG docker $USER
        echo -e "${YELLOW}⚠️  Execute: newgrp docker${NC}"

    elif [ "$DISTRO" == "fedora" ] || [ "$DISTRO" == "rhel" ]; then
        echo "Instalando Docker..."
        sudo dnf install -y docker docker-compose

        echo "Instalando Python 3.11..."
        sudo dnf install -y python3.11 python3.11-devel

        echo "Instalando ferramentas..."
        sudo dnf install -y git curl wget vim nano jq

        sudo usermod -aG docker $USER
    fi
    echo -e "${GREEN}✓ Dependências instaladas${NC}"

elif [ "$OS" == "macos" ]; then
    # Verificar se Homebrew está instalado
    if ! command -v brew &> /dev/null; then
        echo "Instalando Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    echo "Instalando Docker..."
    brew install docker docker-compose

    echo "Instalando Python 3.11..."
    brew install python@3.11

    echo "Instalando ferramentas..."
    brew install git curl wget vim nano jq

    echo -e "${GREEN}✓ Dependências instaladas${NC}"
fi

# ============ VERIFICAR INSTALAÇÕES ============
echo ""
echo -e "${BLUE}[3/8] Verificando instalações...${NC}"

commands=("docker" "docker compose" "python3" "git" "curl")
for cmd in "${commands[@]}"; do
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓ $cmd${NC}"
    else
        echo -e "${RED}✗ $cmd não encontrado${NC}"
    fi
done

# ============ CLONAR/PREPARAR CÓDIGO ============
echo ""
echo -e "${BLUE}[4/8] Preparando código...${NC}"

if [ ! -d ".git" ]; then
    echo "Inicializando git..."
    git init
    git add .
    git commit -m "Initial commit - Logos Auditoria"
fi
echo -e "${GREEN}✓ Código pronto${NC}"

# ============ SETUP PYTHON ============
echo ""
echo -e "${BLUE}[5/8] Setup Python local...${NC}"

echo "Criando virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Atualizando pip..."
pip install --upgrade pip setuptools wheel

echo "Instalando dependências Python..."
pip install -r requirements.txt

echo -e "${GREEN}✓ Python setup completo${NC}"

# ============ CRIAR .env LOCAL ============
echo ""
echo -e "${BLUE}[6/8] Configurando .env local...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Editado .env para desenvolvimento local${NC}"

    # Configurar para local
    sed -i 's|http://localhost:3000|http://localhost:3000|g' .env
    sed -i 's|DEBUG=false|DEBUG=true|g' .env
    sed -i 's|LOG_LEVEL=WARNING|LOG_LEVEL=INFO|g' .env
fi
echo -e "${GREEN}✓ .env configurado${NC}"

# ============ INICIAR DOCKER COMPOSE ============
echo ""
echo -e "${BLUE}[7/8] Iniciando serviços Docker...${NC}"

echo "Buildando imagem..."
docker build -t logos-auditoria:dev .

echo "Iniciando stack Docker..."
docker-compose up -d

echo "Aguardando serviços ficarem saudáveis..."
for i in {1..30}; do
    if curl -s http://localhost:8000/auditoria/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API saudável${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

docker-compose ps
echo -e "${GREEN}✓ Docker Compose rodando${NC}"

# ============ TESTES ============
echo ""
echo -e "${BLUE}[8/8] Rodando testes...${NC}"

pytest test_auditoria.py -v --tb=short || {
    echo -e "${YELLOW}⚠️  Alguns testes falharam - verifique${NC}"
}

echo -e "${GREEN}✓ Testes concluídos${NC}"

# ============ RESUMO FINAL ============
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ SETUP LOCAL COMPLETO!                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Próximos passos:${NC}"
echo ""
echo "1. ${YELLOW}Ativar virtual environment:${NC}"
echo "   source venv/bin/activate"
echo ""
echo "2. ${YELLOW}Rodar servidor localmente:${NC}"
echo "   python servicos_auditoria.py"
echo ""
echo "3. ${YELLOW}Ou via Docker:${NC}"
echo "   docker-compose up"
echo ""
echo "4. ${YELLOW}Acessar dashboard:${NC}"
echo "   http://localhost:8000/docs (Swagger UI)"
echo "   open index.html (Dashboard)"
echo ""
echo "5. ${YELLOW}Monitoramento:${NC}"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "6. ${YELLOW}Comandos úteis:${NC}"
echo "   make help              # Ver todos os comandos"
echo "   make test              # Rodar testes"
echo "   make logs              # Ver logs"
echo "   make shell-mongo       # Acessar MongoDB"
echo ""
echo -e "${BLUE}Documentação:${NC}"
echo "   SETUP.md               # Setup detalhado"
echo "   AUDITORIA_README.md    # Estrutura de dados"
echo "   INTEGRACAO_WEBPOSTO.md # Integração com webPosto"
echo ""
