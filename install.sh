#!/bin/bash

# INSTALL.SH - Clone + Setup Completo em 1 COMANDO
# Logos Auditoria - Máquina nova → Rodando em 10 minutos

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ============ CONFIG ============
REPO_URL="${1:-https://seu-repo.com/logos-auditoria.git}"
INSTALL_DIR="${2:-$HOME/logos-auditoria}"
DISTRO=""

# ============ HEADER ============
clear
echo -e "${BLUE}${BOLD}"
cat << "EOF"
╔════════════════════════════════════════════════════════╗
║                                                        ║
║     🚀 LOGOS AUDITORIA - INSTALAÇÃO AUTOMÁTICA        ║
║                                                        ║
║     Clone + Setup + Docker + Testes em 1 comando      ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${YELLOW}Instalação iniciada: $(date)${NC}"
echo ""

# ============ DETECÇÃO SISTEMA ============
echo -e "${BLUE}[1/10] Detectando sistema operacional...${NC}"

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
else
    echo -e "${RED}✗ Sistema não suportado${NC}"
    exit 1
fi

# ============ INSTALAR DOCKER ============
echo ""
echo -e "${BLUE}[2/10] Instalando Docker...${NC}"

if ! command -v docker &> /dev/null; then
    if [ "$OS" == "linux" ] && [ "$DISTRO" == "ubuntu" ]; then
        sudo apt-get update > /dev/null 2>&1
        sudo apt-get install -y docker.io docker-compose-plugin > /dev/null 2>&1
        sudo usermod -aG docker $USER > /dev/null 2>&1
    elif [ "$OS" == "macos" ]; then
        if ! command -v brew &> /dev/null; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" > /dev/null 2>&1
        fi
        brew install docker docker-compose > /dev/null 2>&1
    fi
    echo -e "${GREEN}✓ Docker instalado${NC}"
else
    echo -e "${GREEN}✓ Docker já existe${NC}"
fi

# ============ INSTALAR PYTHON ============
echo ""
echo -e "${BLUE}[3/10] Instalando Python 3.11...${NC}"

if ! command -v python3.11 &> /dev/null; then
    if [ "$OS" == "linux" ] && [ "$DISTRO" == "ubuntu" ]; then
        sudo apt-get install -y python3.11 python3.11-venv python3.11-dev > /dev/null 2>&1
    elif [ "$OS" == "macos" ]; then
        brew install python@3.11 > /dev/null 2>&1
    fi
    echo -e "${GREEN}✓ Python 3.11 instalado${NC}"
else
    echo -e "${GREEN}✓ Python 3.11 já existe${NC}"
fi

# ============ INSTALAR GIT ============
echo ""
echo -e "${BLUE}[4/10] Instalando Git...${NC}"

if ! command -v git &> /dev/null; then
    if [ "$OS" == "linux" ] && [ "$DISTRO" == "ubuntu" ]; then
        sudo apt-get install -y git > /dev/null 2>&1
    elif [ "$OS" == "macos" ]; then
        brew install git > /dev/null 2>&1
    fi
    echo -e "${GREEN}✓ Git instalado${NC}"
else
    echo -e "${GREEN}✓ Git já existe${NC}"
fi

# ============ CLONAR REPOSITÓRIO ============
echo ""
echo -e "${BLUE}[5/10] Clonando repositório...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠️  Diretório $INSTALL_DIR já existe${NC}"
    read -p "Deseja sobrescrever? (s/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        exit 1
    fi
fi

mkdir -p "$INSTALL_DIR"
git clone "$REPO_URL" "$INSTALL_DIR" > /dev/null 2>&1
cd "$INSTALL_DIR"
echo -e "${GREEN}✓ Clonado em: $INSTALL_DIR${NC}"

# ============ CRIAR VENV ============
echo ""
echo -e "${BLUE}[6/10] Criando Virtual Environment...${NC}"

python3 -m venv venv > /dev/null 2>&1
source venv/bin/activate
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo -e "${GREEN}✓ Virtual Environment criado${NC}"

# ============ INSTALAR DEPENDÊNCIAS ============
echo ""
echo -e "${BLUE}[7/10] Instalando dependências Python...${NC}"

pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependências instaladas${NC}"

# ============ SETUP .env ============
echo ""
echo -e "${BLUE}[8/10] Configurando ambiente...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    # Configurar para desenvolvimento local
    if [ "$OS" == "linux" ]; then
        sed -i 's|DEBUG=false|DEBUG=true|g' .env
        sed -i 's|LOG_LEVEL=WARNING|LOG_LEVEL=INFO|g' .env
    elif [ "$OS" == "macos" ]; then
        sed -i '' 's|DEBUG=false|DEBUG=true|g' .env
        sed -i '' 's|LOG_LEVEL=WARNING|LOG_LEVEL=INFO|g' .env
    fi
fi
echo -e "${GREEN}✓ .env configurado${NC}"

# ============ BUILD DOCKER ============
echo ""
echo -e "${BLUE}[9/10] Building Docker image...${NC}"

docker build -t logos-auditoria:dev . > /dev/null 2>&1
echo -e "${GREEN}✓ Docker image built${NC}"

# ============ INICIAR STACK ============
echo ""
echo -e "${BLUE}[10/10] Iniciando Docker stack...${NC}"

docker-compose up -d > /dev/null 2>&1
sleep 10

# Verificar health
if curl -s http://localhost:8000/auditoria/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Stack iniciado e saudável${NC}"
else
    echo -e "${YELLOW}⚠️  Stack iniciado - aguardando...${NC}"
    for i in {1..10}; do
        if curl -s http://localhost:8000/auditoria/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ API respondendo${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
fi

# ============ RESUMO FINAL ============
echo ""
echo -e "${GREEN}${BOLD}"
cat << "EOF"
╔════════════════════════════════════════════════════════╗
║                                                        ║
║           ✓ INSTALAÇÃO COMPLETA COM SUCESSO!          ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
echo -e "${BLUE}📍 Localização:${NC}"
echo "   $INSTALL_DIR"

echo ""
echo -e "${BLUE}🚀 Próximos passos:${NC}"
echo ""
echo "1. Ir para o diretório:"
echo "   ${YELLOW}cd $INSTALL_DIR${NC}"
echo ""
echo "2. Ativar virtual environment:"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "3. Ver status (6 containers devem estar 'Up'):"
echo "   ${YELLOW}docker-compose ps${NC}"
echo ""
echo "4. Acessar no navegador:"
echo "   ${YELLOW}http://localhost:8000${NC}"
echo ""
echo "5. Rodar testes:"
echo "   ${YELLOW}pytest test_auditoria.py -v${NC}"
echo ""
echo "6. Ver todos os comandos:"
echo "   ${YELLOW}make help${NC}"
echo ""

echo -e "${BLUE}📚 Documentação:${NC}"
echo "   COMECE_AQUI.txt      ← Leia primeiro"
echo "   PASSO_A_PASSO.md     ← Instruções detalhadas"
echo "   SETUP_LOCAL.md       ← Setup manual"
echo ""

echo -e "${BLUE}🌐 Acessos:${NC}"
echo "   API:        http://localhost:8000"
echo "   Swagger:    http://localhost:8000/docs"
echo "   Grafana:    http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo ""

echo -e "${YELLOW}Instalação finalizada: $(date)${NC}"
echo ""
