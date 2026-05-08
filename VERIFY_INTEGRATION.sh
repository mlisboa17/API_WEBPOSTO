#!/bin/bash

# Integration Verification Script - PASSO 7-8
# Tests docker-compose configuration and file structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  WebPosto Integration Verification (P7-P8)"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNING=0

test_file() {
    local file="$1"
    local description="$2"

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $description: $file (NOT FOUND)"
        ((FAILED++))
    fi
}

test_yaml_syntax() {
    local file="$1"
    local description="$2"

    if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description: Valid YAML syntax"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $description: Invalid YAML syntax"
        ((FAILED++))
    fi
}

test_content() {
    local file="$1"
    local pattern="$2"
    local description="$3"

    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $description"
        ((FAILED++))
    fi
}

# =============================================
# File Structure Tests
# =============================================

echo "📋 File Structure Tests"
echo "----------------------"

test_file "index.html" "Consolidated dashboard"
test_file "docker-compose.yml" "Docker Compose config"
test_file "Dockerfile.webposto" "WebPosto Dockerfile"
test_file "INTEGRATION_STEPS_7_8_COMPLETE.md" "Integration documentation"
test_file "WebPosto_API/requirements.txt" "WebPosto requirements"
test_file "WebPosto_API/main.py" "WebPosto main entry point"

echo ""

# =============================================
# Configuration Tests
# =============================================

echo "⚙️  Configuration Tests"
echo "---------------------"

test_yaml_syntax "docker-compose.yml" "docker-compose.yml"
test_content "docker-compose.yml" "webposto-api" "API container naming"
test_content "docker-compose.yml" "Dockerfile.webposto" "Dockerfile reference"
test_content "docker-compose.yml" "webposto-db" "MongoDB container naming"
test_content "docker-compose.yml" "webposto-nginx" "Nginx container naming"
test_content "docker-compose.yml" "webposto-prometheus" "Prometheus container naming"
test_content "docker-compose.yml" "webposto-grafana" "Grafana container naming"

echo ""

# =============================================
# Dashboard Tests
# =============================================

echo "📊 Dashboard Tests"
echo "------------------"

test_content "index.html" "ConsolidatedDashboard" "Main React component"
test_content "index.html" "DashboardAuditoria" "Audit dashboard component"
test_content "index.html" "DashboardAbastecimento" "Fuel dashboard component"
test_content "index.html" "DashboardVendas" "Sales dashboard component"
test_content "index.html" "tabbed" "Tab navigation implementation"
test_content "index.html" "localhost:8000" "API endpoint configuration"

echo ""

# =============================================
# Service Configuration Tests
# =============================================

echo "🔧 Service Configuration Tests"
echo "-------------------------------"

test_content "docker-compose.yml" "8000:8000" "API port mapping"
test_content "docker-compose.yml" "27017:27017" "MongoDB port mapping"
test_content "docker-compose.yml" "6379:6379" "Redis port mapping"
test_content "docker-compose.yml" "80:80" "HTTP port mapping"
test_content "docker-compose.yml" "443:443" "HTTPS port mapping"
test_content "docker-compose.yml" "9090:9090" "Prometheus port mapping"
test_content "docker-compose.yml" "3000:3000" "Grafana port mapping"

echo ""

# =============================================
# Dockerfile Tests
# =============================================

echo "🐳 Dockerfile Tests"
echo "-------------------"

test_content "Dockerfile.webposto" "multi-stage" "Multi-stage build" || \
    test_content "Dockerfile.webposto" "as builder" "Builder stage"

test_content "Dockerfile.webposto" "python:3.11" "Python 3.11 base image"
test_content "Dockerfile.webposto" "webposto" "Non-root user"
test_content "Dockerfile.webposto" "HEALTHCHECK" "Health check definition"
test_content "Dockerfile.webposto" "EXPOSE 8000" "Port exposure"

echo ""

# =============================================
# Environment Variables Tests
# =============================================

echo "🔐 Environment Variables"
echo "------------------------"

test_content "docker-compose.yml" "DATABASE_URL" "WebPosto database URL"
test_content "docker-compose.yml" "REDIS_URL" "Redis URL"
test_content "docker-compose.yml" "LOGOS_SPACE_DB" "Legacy database support"
test_content "docker-compose.yml" "WEBPOSTO_BASE_URL" "Legacy API configuration"

echo ""

# =============================================
# Health Check Tests
# =============================================

echo "❤️  Health Checks"
echo "----------------"

test_content "docker-compose.yml" "healthcheck:" "Health check definitions"
test_content "docker-compose.yml" "auditoria/health" "API health endpoint"
test_content "docker-compose.yml" "mongosh" "MongoDB health check"
test_content "docker-compose.yml" "redis-cli" "Redis health check"
test_content "docker-compose.yml" "prometheus" "Prometheus health check"

echo ""

# =============================================
# Backward Compatibility Tests
# =============================================

echo "🔄 Backward Compatibility"
echo "------------------------"

test_content "docker-compose.yml" "LOGOS_EYE_ENABLED" "Legacy Eye integration"
test_content "docker-compose.yml" "LOGOS_SPACE_ENABLED" "Legacy Space support"
test_content "docker-compose.yml" "logos" "Legacy database name"
test_content "docker-compose.yml" "logos-network" "Shared network"

echo ""

# =============================================
# Summary
# =============================================

echo "================================================"
echo "  Test Summary"
echo "================================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNING${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure .env file with credentials"
    echo "2. Run: docker-compose up -d"
    echo "3. Wait for services to start"
    echo "4. Access dashboard: http://localhost"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review.${NC}"
    exit 1
fi
