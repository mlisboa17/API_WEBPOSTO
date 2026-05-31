#!/bin/bash
# GEMINI 2.0: Frontend Health Check Script
# Validates Reflex frontend + Redis state + Asset delivery

set -e

# Configuration
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
REDIS_URL="${REDIS_URL:-redis://redis:6379/1}"
HEALTHCHECK_TIMEOUT="${HEALTHCHECK_TIMEOUT:-5}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0

# Health check functions
check_frontend() {
    echo -n "🌐 Frontend health: "
    if curl -sf --max-time $HEALTHCHECK_TIMEOUT "$FRONTEND_URL/_next/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_redis() {
    echo -n "💾 Redis state: "
    if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠ (optional)${NC}"
        ((CHECKS_PASSED++))  # Optional check
        return 0
    fi
}

check_assets() {
    echo -n "📦 Static assets: "
    if curl -sf --max-time $HEALTHCHECK_TIMEOUT -I "$FRONTEND_URL/_next/static/index.html" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_memory() {
    echo -n "🧠 Memory available: "
    MEMORY_USAGE=$(free | awk 'NR==2{printf("%.0f", $3/$2 * 100.0)}')
    if [ "$MEMORY_USAGE" -lt 85 ]; then
        echo -e "${GREEN}$MEMORY_USAGE%${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${YELLOW}$MEMORY_USAGE% (high)${NC}"
        ((CHECKS_PASSED++))
        return 0
    fi
}

# Run health checks
echo "🏥 Frontend Health Check"
echo "========================"
check_frontend
check_redis
check_assets
check_memory

# Report
echo ""
echo "📊 Results: $CHECKS_PASSED passed, $CHECKS_FAILED failed"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend is healthy${NC}"
    exit 0
else
    echo -e "${RED}❌ Frontend health check failed${NC}"
    exit 1
fi
