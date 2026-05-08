# 🐳 Docker Deployment — webPosto Sync Service

**Pronto para deployar em qualquer servidor Linux com Docker + Docker Compose**

---

## ✅ Pré-requisitos

```bash
docker --version    # >= 20.10
docker-compose --version  # >= 2.0
```

**Instalar (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com | sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

---

## 🚀 Deployment em 3 Passos

### 1️⃣ Clone ou copie o projeto
```bash
cd /opt/webposto-api
ls -la  # Deve ter: Dockerfile, docker-compose.yml, .env
```

### 2️⃣ Rodar o container
```bash
docker-compose up -d

# Verificar status
docker-compose ps
docker-compose logs -f api
```

### 3️⃣ Testar
```bash
curl http://localhost:8000/health

# Resposta esperada:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "webposto_api": "http://web.qualityautomacao.com.br",
#   "empresa": "POSTO VIP..."
# }
```

---

## 📋 Estrutura de Serviços

```
┌─────────────────────────┐
│   webPosto API (8000)   │◄─── curl http://localhost:8000
└────────────┬────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼──────┐   ┌─────▼──────┐
│  Redis   │   │ PostgreSQL  │
│ (6379)   │   │  (5432)     │
└──────────┘   │ (opcional)  │
               └─────────────┘
```

---

## 🔧 Variáveis de Ambiente

**Arquivo: `.env`**
```bash
WEBPOSTO_API_KEY=<WEBPOSTO_API_TOKEN>
WEBPOSTO_BASE_URL=http://web.qualityautomacao.com.br
DATABASE_URL=sqlite+aiosqlite:///./webposto.db
REDIS_URL=redis://redis:6379/0
API_PORT=8000
DEBUG=False
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Para produção com PostgreSQL:**
```bash
DATABASE_URL=postgresql+asyncpg://webposto:senha_segura@postgres:5432/webposto
```

---

## 🎯 Operações Comuns

### Build da imagem
```bash
docker-compose build --no-cache
```

### Ver logs em tempo real
```bash
docker-compose logs -f api
```

### Parar containers
```bash
docker-compose down
```

### Parar e remover dados
```bash
docker-compose down -v  # Remove volumes
```

### Entrar no container (shell)
```bash
docker-compose exec api bash
```

### Restartar API
```bash
docker-compose restart api
```

---

## 🔍 Troubleshooting

### Erro: "Cannot connect to webPosto API"
**Problema:** Firewall/rede bloqueando `web.qualityautomacao.com.br`

**Solução:**
```bash
# Testar conectividade do container
docker-compose exec api curl -I http://web.qualityautomacao.com.br

# Verificar DNS
docker-compose exec api nslookup web.qualityautomacao.com.br
```

### Erro: "Port 8000 already in use"
```bash
# Ver quem está usando a porta
lsof -i :8000

# Mudar porta em docker-compose.yml
# Alterar: "8000:8000" para "8001:8000"
docker-compose up -d
```

### Container sai logo após iniciar
```bash
# Ver logs de erro
docker-compose logs api

# Verificar .env está correto
cat .env | grep WEBPOSTO
```

### Redis não conecta
```bash
# Reiniciar Redis
docker-compose restart redis

# Testar conexão
docker-compose exec api redis-cli -h redis ping
# Deve responder: PONG
```

---

## 📊 Monitoring

### Ver métricas de uso
```bash
docker stats webposto-api
```

### Ver disk usage
```bash
docker system df
```

### Limpar cache/unused containers
```bash
docker system prune -a
```

---

## 🔐 Segurança em Produção

### 1. Mudar senha do PostgreSQL (se usar)
```yaml
# docker-compose.yml
environment:
  POSTGRES_PASSWORD: sua_senha_muito_segura_aqui
```

### 2. Usar secrets do Docker (recomendado)
```bash
echo "sua_chave_api" | docker secret create webposto_api_key -
echo "sua_senha_db" | docker secret create postgres_password -
```

### 3. Usar reverse proxy (nginx/Traefik)
```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name api.seudominio.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Limitar recursos
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

---

## 🚀 Deploy em VPS/Cloud

### AWS EC2
```bash
# Conectar via SSH
ssh -i chave.pem ec2-user@seu-ip

# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Clonar projeto
git clone seu-repo /opt/webposto-api
cd /opt/webposto-api

# Rodar
docker-compose up -d
```

### DigitalOcean / Linode
```bash
# Mesmo processo, SSH para o servidor
# Rodar: docker-compose up -d
```

### Heroku (alternativo)
```bash
# Heroku Procfile:
web: gunicorn -w 4 -b 0.0.0.0:$PORT src.main_minimal:app

# Deploy:
heroku create seu-app
git push heroku main
```

---

## 📈 Scaling (Múltiplas Instâncias)

### Docker Swarm (simples)
```bash
docker swarm init
docker stack deploy -c docker-compose.yml webposto
```

### Kubernetes (recomendado para produção)
```yaml
# webposto-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webposto-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webposto
  template:
    metadata:
      labels:
        app: webposto
    spec:
      containers:
      - name: api
        image: seu-registry/webposto:latest
        ports:
        - containerPort: 8000
```

Deploy:
```bash
kubectl apply -f webposto-deployment.yaml
kubectl expose deployment webposto-api --type=LoadBalancer --port=80 --target-port=8000
```

---

## 🔄 CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Docker Hub

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and push
        uses: docker/build-push-action@v2
        with:
          push: true
          tags: seu-docker-hub/webposto:latest
```

### GitLab CI
```yaml
# .gitlab-ci.yml
deploy:
  stage: deploy
  script:
    - docker build -t webposto:latest .
    - docker push seu-registry/webposto:latest
  only:
    - main
```

---

## 📞 Suporte

**Problemas?**
1. Verificar logs: `docker-compose logs api`
2. Checar conectividade: `docker-compose exec api curl http://web.qualityautomacao.com.br`
3. Verificar .env: Valores corretos?
4. Restartar: `docker-compose down && docker-compose up -d`

---

**Versão:** 0.1.0  
**Última atualização:** 13/04/2026  
**Mantido por:** Grupo Lisboa
