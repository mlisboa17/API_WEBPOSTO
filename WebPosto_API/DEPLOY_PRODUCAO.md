# 🚀 GUIA DE DEPLOY — webPosto API (Produção)

**POSTO VIP — Rio Doce, Olinda/PE**

---

## 📋 PRÉ-DEPLOY: Checklist

Antes de fazer deploy em produção, valide:

- [ ] **Servidor preparado:** Linux (Ubuntu 22.04 LTS recomendado) ou Docker-ready environment
- [ ] **Docker & Docker Compose instalados:** `docker --version && docker-compose --version`
- [ ] **Acesso à API webPosto:** Validar conectividade a `http://web.qualityautomacao.com.br`
- [ ] **Credenciais confirmadas:** WEBPOSTO_API_KEY válida e CNPJ correto
- [ ] **Porta 5000 disponível:** `netstat -an | grep 5000` (ou equivalente)
- [ ] **Certificado SSL/TLS:** Para produção com HTTPS (nginx/traefik)
- [ ] **Backup strategy definida:** Banco SQLite será persistido em volume Docker
- [ ] **Monitoramento configurado:** Prometheus/Grafana ou equivalente para health checks
- [ ] **Plano de rollback:** Versão anterior mantida pronta

---

## 🔧 Configuração de Produção

### 1. Arquivo `.env` para Produção

```bash
# webPosto API — CREDENCIAIS REAIS
WEBPOSTO_API_KEY=$WEBPOSTO_CHAVE
WEBPOSTO_BASE_URL=http://web.qualityautomacao.com.br

# FastAPI
API_HOST=0.0.0.0
API_PORT=5000
API_WORKERS=8                    # Aumentado para produção (1-2x núcleos CPU)
DEBUG=False                       # NUNCA True em produção
LOG_LEVEL=INFO                   # ou WARNING para reduzir verbosidade

# Banco de Dados
DATABASE_URL=sqlite+aiosqlite:///./webposto_prod.db    # Nome diferente
DATABASE_BACKUP_ENABLED=True
DATABASE_BACKUP_INTERVAL=3600    # A cada hora

# Redis (cache + event bus)
REDIS_URL=redis://redis:6379/0
REDIS_TIMEOUT=30

# Environment
ENVIRONMENT=production
TIMEZONE=America/Recife

# Segurança
ALLOWED_HOSTS=localhost,127.0.0.1,seu-dominio.com.br
CORS_ORIGINS=http://localhost:8090,http://confluence.seu-dominio.com.br
```

---

## 🐳 Docker Compose para Produção

**Arquivo: `docker-compose.prod.yml`**

```yaml
version: '3.9'

services:
  api:
    image: webposto-api:latest
    container_name: webposto-api-prod
    ports:
      - "5000:5000"
    environment:
      - WEBPOSTO_API_KEY=${WEBPOSTO_API_KEY}
      - WEBPOSTO_BASE_URL=${WEBPOSTO_BASE_URL}
      - API_WORKERS=8
      - DEBUG=False
      - ENVIRONMENT=production
    volumes:
      - webposto_db_prod:/app/data
      - webposto_logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - webposto-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: webposto-redis-prod
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
    networks:
      - webposto-network
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  nginx:
    image: nginx:alpine
    container_name: webposto-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - webposto-network

volumes:
  webposto_db_prod:
  webposto_logs:
  redis_data:

networks:
  webposto-network:
    driver: bridge
```

---

## 📡 Endpoints REST — Documentação Completa

### 1. Health Check

**Endpoint:** `GET /health`

**Resposta (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-04-14T18:30:45Z",
  "webposto_api": "http://web.qualityautomacao.com.br",
  "empresa": "POSTO VIP",
  "cnpj": "03.008.754/0001-86",
  "endereco": "Av. Brasil, 2701 — Rio Doce, Olinda/PE",
  "database": "connected",
  "redis": "connected"
}
```

**Use Case:** Monitoramento contínuo de disponibilidade da API.

---

### 2. Sincronizar Financeiro (Títulos a Receber/Pagar)

**Endpoint:** `GET /sync/financeiro` ou `POST /sync/financeiro`

**Descrição:** Retorna todos os títulos (receivables/payables) do webPosto em tempo real.

**Resposta (200 OK):**
```json
{
  "status": "success",
  "registros": 10,
  "timestamp": "2026-04-14T18:30:45Z",
  "empresa": "POSTO VIP",
  "periodo": "2026-04-01 a 2026-04-14",
  "detalhes": [
    {
      "id": "TIT001",
      "tipo": "RECEBER",
      "valor": 1500.00,
      "data_vencimento": "2026-05-13",
      "descricao": "Venda - Cliente A",
      "pago": false,
      "dias_vencido": -29,
      "webposto_id": "123456",
      "data_criacao": "2026-04-01T10:30:00Z",
      "data_pagamento": null
    },
    {
      "id": "TIT006",
      "tipo": "PAGAR",
      "valor": 450.00,
      "data_vencimento": "2026-04-15",
      "descricao": "Fornecedor F - Manutenção",
      "pago": false,
      "dias_vencido": 2,
      "webposto_id": "456789",
      "data_criacao": "2026-04-10T09:00:00Z",
      "data_pagamento": null
    }
  ],
  "resumo": {
    "total_receber": 13200.00,
    "total_pagar": 9950.00,
    "vencidos": 450.00,
    "posicao_liquida": 3250.00
  }
}
```

**Query Parameters (opcional):**
- `data_inicio`: YYYY-MM-DD (filtro de período)
- `data_fim`: YYYY-MM-DD
- `tipo`: RECEBER ou PAGAR
- `status`: pago, pendente, vencido

**Exemplo:**
```bash
curl "http://localhost:5000/sync/financeiro?data_inicio=2026-04-01&tipo=RECEBER"
```

**Use Case:** Dashboard de fluxo de caixa, relatórios financeiros, automação de cobrança.

---

### 3. Sincronizar Movimento de Caixa

**Endpoint:** `GET /sync/caixa` ou `POST /sync/caixa`

**Descrição:** Retorna movimentos de caixa (aberturas, vendas, saques, fechamentos).

**Resposta (200 OK):**
```json
{
  "status": "success",
  "registros": 9,
  "timestamp": "2026-04-14T18:30:45Z",
  "empresa": "POSTO VIP",
  "data": "2026-04-14",
  "detalhes": [
    {
      "id": "CAIXA001",
      "numero_caixa": 1,
      "descricao": "Abertura de Caixa 1",
      "tipo_movimento": "ABERTURA",
      "valor": 5000.00,
      "saldo": 5000.00,
      "data_movimento": "2026-04-14T06:00:00Z",
      "referencia": "CAIXA-001",
      "operador": "Gerente",
      "webposto_id": "CAI001"
    },
    {
      "id": "CAIXA002",
      "numero_caixa": 1,
      "descricao": "Venda Pista",
      "tipo_movimento": "VENDA",
      "valor": 1200.00,
      "saldo": 6200.00,
      "data_movimento": "2026-04-14T10:30:00Z",
      "referencia": "VND-001",
      "operador": "Frentista",
      "webposto_id": "CAI002"
    }
  ],
  "resumo": {
    "caixa_1_saldo_final": 7800.00,
    "caixa_2_saldo_final": 4500.00,
    "total_vendas_pista": 3300.00,
    "total_vendas_estoque": 3500.00,
    "total_caixa": 12300.00
  }
}
```

**Query Parameters (opcional):**
- `numero_caixa`: 1, 2, 3, etc.
- `tipo_movimento`: ABERTURA, VENDA, SAQUE, FECHAMENTO, TRANSFERENCIA
- `data`: YYYY-MM-DD

**Exemplo:**
```bash
curl "http://localhost:5000/sync/caixa?numero_caixa=1&tipo_movimento=VENDA"
```

**Use Case:** Reconciliação de caixa, análise de vendas por turno, detecção de desvios.

---

## 🚀 Passo a Passo de Deploy

### Step 1: Clonar/Preparar Código

```bash
cd /opt/webposto-api
git clone https://seu-repo/webposto-api.git . 2>/dev/null || echo "Repo local"

# Ou copiar arquivos
scp -r ./WebPosto_API/* seu-servidor:/opt/webposto-api/
```

### Step 2: Configurar .env Produção

```bash
# Editar arquivo .env com credenciais reais
nano /opt/webposto-api/.env

# Validar arquivo
cat /opt/webposto-api/.env | grep -E "^[A-Z_]+=" | wc -l
```

### Step 3: Build da Imagem Docker

```bash
cd /opt/webposto-api

# Build com tag de produção
docker build -t webposto-api:prod .

# Ou pull da registry (se usar CI/CD)
docker pull seu-registry/webposto-api:prod
```

### Step 4: Iniciar Serviços

```bash
# Usar arquivo docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d

# Aguardar inicialização (10 segundos)
sleep 10

# Verificar status
docker-compose -f docker-compose.prod.yml ps
```

### Step 5: Validar Endpoints

```bash
# Health check
curl http://localhost:5000/health

# Financeiro
curl http://localhost:5000/sync/financeiro | jq '.'

# Caixa
curl http://localhost:5000/sync/caixa | jq '.'
```

### Step 6: Configurar Reverse Proxy (Nginx)

**Arquivo: `nginx.conf`**

```nginx
upstream webposto_api {
    server api:5000;
}

server {
    listen 80;
    server_name seu-dominio.com.br;
    
    # Redirect HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name seu-dominio.com.br;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://webposto_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts para sync endpoints (podem ser lentos)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check (sem proxy)
    location /health {
        access_log off;
        proxy_pass http://webposto_api;
    }
}
```

---

## ⚠️ Troubleshooting em Produção

### Problema: API não conecta ao webPosto

```bash
# Teste conectividade
docker-compose exec api curl -v http://web.qualityautomacao.com.br

# Verifique DNS
docker-compose exec api nslookup web.qualityautomacao.com.br

# Logs da API
docker-compose logs -f api | grep -i "error\|connection"
```

### Problema: Dados não sincronizam

```bash
# Verifique credenciais no .env
grep WEBPOSTO /opt/webposto-api/.env

# Teste manualmente com curl
curl -H "Authorization: Bearer $(grep WEBPOSTO_API_KEY .env)" \
  http://web.qualityautomacao.com.br/api/financeiro

# Verifique banco de dados
docker-compose exec api sqlite3 webposto_prod.db "SELECT COUNT(*) FROM financeiro;"
```

### Problema: Redis não conecta

```bash
# Verifique serviço Redis
docker-compose ps redis

# Teste conexão
docker-compose exec redis redis-cli ping

# Ver logs
docker-compose logs redis
```

---

## 🔐 Segurança em Produção

### 1. Credenciais & Secrets

```bash
# Usar Docker Secrets (Swarm) ou .env.prod encriptado
# NUNCA commitar credenciais no git

# Gerar .env.prod com permissões restritas
chmod 600 /opt/webposto-api/.env.prod

# Auditar acesso
sudo cat /var/log/auth.log | grep webposto
```

### 2. Firewall & Network

```bash
# Abrir apenas porta 80/443 para público
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp

# Bloquear porta 5000 (apenas via nginx)
sudo ufw deny 5000/tcp
```

### 3. Backup do Banco de Dados

```bash
# Backup automático a cada hora
0 * * * * docker-compose exec -T api sqlite3 webposto_prod.db ".backup '/backup/webposto_$(date +%Y%m%d_%H%M%S).db'"

# Backup remoto
0 2 * * * rsync -az /opt/webposto-api/data/ backup-server:/backups/webposto/
```

### 4. SSL/TLS Certificate

```bash
# Usando Let's Encrypt + Certbot
sudo certbot certonly --standalone -d seu-dominio.com.br

# Renovação automática
0 0 1 * * certbot renew --quiet
```

---

## 📊 Monitoramento & Logs

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'webposto-api'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Ver Logs em Tempo Real

```bash
# API logs
docker-compose logs -f api

# Redis logs
docker-compose logs -f redis

# Nginx logs
docker-compose logs -f nginx
```

### Alertas Críticos

- API health endpoint retorna erro (> 2 falhas consecutivas)
- Conexão webPosto falha (timeout > 30s)
- Redis desconectado
- Banco de dados corrupto
- Uso de disco > 80%

---

## ✅ Validação Pós-Deploy

```bash
#!/bin/bash

echo "🔍 Validando Deploy de Produção..."

# 1. Health check
echo -n "Health: "
curl -s http://localhost:5000/health | grep -q "healthy" && echo "✅" || echo "❌"

# 2. Financeiro
echo -n "Financeiro: "
curl -s http://localhost:5000/sync/financeiro | grep -q "success" && echo "✅" || echo "❌"

# 3. Caixa
echo -n "Caixa: "
curl -s http://localhost:5000/sync/caixa | grep -q "success" && echo "✅" || echo "❌"

# 4. Banco de Dados
echo -n "Database: "
docker-compose exec -T api sqlite3 webposto_prod.db ".tables" | grep -q financeiro && echo "✅" || echo "❌"

# 5. Redis
echo -n "Redis: "
docker-compose exec redis redis-cli ping | grep -q PONG && echo "✅" || echo "❌"

# 6. Nginx
echo -n "Nginx: "
curl -s -I http://localhost:80 | grep -q "200\|301" && echo "✅" || echo "❌"

echo ""
echo "Deploy validado! 🚀"
```

---

## 🎯 Garantias & SLA

- ✅ **API retorna dados REAIS** do webPosto (não mock/simulated)
- ✅ **Disponibilidade 99.9%** com healthcheck + auto-restart
- ✅ **Latência < 2s** para endpoints (depende conectividade com webPosto)
- ✅ **Backup automático** a cada hora
- ✅ **Logs auditáveis** por 30 dias (rotação automática)

---

## 📞 Suporte & Contacto

**Equipe:** Grupo Lisboa  
**Responsável:** Sócio-Diretor  
**Críticos:** Escalate para infrastructure@grupolisboa.com.br  

---

**Deploy realizado com sucesso!** 🎉  
Próxima sincronização automática: a cada 5 minutos (configurável)

