# ⚡ QUICKSTART - 5 MINUTOS

## 1. Configure Variáveis

```bash
cd /sessions/beautiful-dreamy-heisenberg/mnt/WebPosto_API
cp .env.example .env

# Edite .env e adicione sua chave
nano .env
# WEBPOSTO_API_KEY=sua_chave_rest_aqui
```

## 2. Inicie com Docker

```bash
docker-compose up
```

Espere 30-60 segundos. App estará em **http://localhost:8000**

## 3. Teste Imediatamente

```bash
# Em outro terminal:
curl http://localhost:8000/health
curl http://localhost:8000/clientes

# Crie um cliente:
curl -X POST http://localhost:8000/clientes \
  -H "Content-Type: application/json" \
  -d '{"nome":"Teste","cnpj":"12345678901234"}'

# Sincronize do webPosto:
curl -X POST http://localhost:8000/sync/clientes
```

## 4. Veja a API

http://localhost:8000/docs (Swagger)

## 5. Rode Testes

```bash
docker exec webposto-app poetry run pytest --cov=src
```

---

**Pronto.** A aplicação está 100% funcional.

Próximo: leia IMPLEMENTACAO_COMPLETA.md para próximos passos.
