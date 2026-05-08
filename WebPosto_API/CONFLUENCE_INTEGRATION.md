# 🔗 Integração webPosto API + Confluence

**APIs Separadas**
- webPosto API: `http://localhost:5000`
- Confluence: `http://localhost:8090`

---

## 🚀 Instalação em 5 Passos

### 1️⃣ Rodar o Setup Automatizado

```bash
cd /sessions/gallant-zealous-bohr/mnt/WebPosto_API
chmod +x setup_ambiente.sh
./setup_ambiente.sh
```

**Resultado esperado:**
```
✅ Setup completo!
📊 Status dos containers:
   webposto-redis: Up
   webposto-api: Up

📡 Endpoints disponíveis:
   http://localhost:5000/health
   http://localhost:5000/sync/financeiro
   http://localhost:5000/sync/caixa
```

---

### 2️⃣ Verificar API está rodando

```bash
curl http://localhost:5000/health

# Resposta esperada:
# {
#   "status": "healthy",
#   "version": "0.1.0",
#   "webposto_api": "http://web.qualityautomacao.com.br",
#   "empresa": "POSTO VIP..."
# }
```

---

### 3️⃣ Usar o Plugin Python em Confluence

**Opção A: Via REST Call em Confluence**

1. Em Confluence, vá para: **Admin** → **Webhooks** ou **Automação**
2. Configure webhook que chama:
   ```
   GET http://localhost:5000/sync/financeiro
   GET http://localhost:5000/sync/caixa
   ```

**Opção B: Via Python/Script**

```python
from confluence_plugin_webposto import WebPostoConfluencePlugin
import asyncio

async def sync_webposto():
    plugin = WebPostoConfluencePlugin(api_url="http://localhost:5000")
    
    # Verificar saúde
    health = await plugin.check_health()
    print(f"API: {'✅ Online' if health else '❌ Offline'}")
    
    # Buscar dados
    data = await plugin.get_all_data()
    
    # Formatar para Confluence
    confluence_content = await plugin.create_confluence_page_content(data)
    print(confluence_content)

asyncio.run(sync_webposto())
```

**Opção C: Via cron job (sincronização automática)**

```bash
# /etc/cron.d/webposto-sync
# Rodar a cada 1 hora
0 * * * * python3 /opt/webposto-api/confluence-plugin-webposto.py
```

---

### 4️⃣ Integração com Confluence Macro

**Opção 1: Macro customizada em Confluence**

```html
<!-- Adicionar em página Confluence -->
<ac:structured-macro ac:name="webposto-sync">
    <ac:parameter ac:name="api-url">http://localhost:5000</ac:parameter>
    <ac:parameter ac:name="refresh">60</ac:parameter>
</ac:structured-macro>
```

**Opção 2: Via iFrame**

```html
<!-- Em página Confluence -->
<iframe 
    src="http://localhost:5000/sync/financeiro"
    width="100%"
    height="600"
></iframe>
```

**Opção 3: Via JavaScript em Confluence**

```javascript
// Adicionar script customizado
fetch('http://localhost:5000/sync/financeiro')
    .then(r => r.json())
    .then(data => {
        document.getElementById('financeiro-table').innerHTML = formatarTabela(data);
    });
```

---

### 5️⃣ Criar Página Confluence Automaticamente

```bash
# Script para criar página com dados atualizados
python3 << 'EOF'
import asyncio
import json
from confluence_plugin_webposto import WebPostoConfluencePlugin

async def criar_pagina():
    plugin = WebPostoConfluencePlugin(api_url="http://localhost:5000")
    data = await plugin.get_all_data()
    
    # Salvar JSON
    with open("webposto_data.json", "w") as f:
        json.dump(data, f, indent=2)
    
    # Formatar para Confluence
    content = await plugin.create_confluence_page_content(data)
    
    # Salvar em arquivo
    with open("confluence_page.html", "w") as f:
        f.write(content)
    
    print("✅ Página criada: confluence_page.html")

asyncio.run(criar_pagina())
EOF
```

---

## 📊 Exemplos de Dados

### Financeiro
```json
{
  "status": "success",
  "registros": 13,
  "timestamp": "2026-04-13T10:30:45",
  "detalhes": [
    {
      "id": "TIT001",
      "tipo": "RECEBER",
      "valor": 1500.00,
      "data_vencimento": "2026-05-13",
      "descricao": "Venda - Cliente A",
      "pago": false,
      "webposto_id": "123456"
    }
  ]
}
```

### Caixa
```json
{
  "status": "success",
  "registros": 4,
  "timestamp": "2026-04-13T10:30:45",
  "detalhes": [
    {
      "id": "CAIXA001",
      "descricao": "Abertura de Caixa 1",
      "saldo": 5000.00,
      "data_movimento": "2026-04-13T06:00:00",
      "referencia": "CAIXA-001",
      "webposto_id": "CAI001"
    }
  ]
}
```

---

## 🔧 Troubleshooting

### API não conecta
```bash
# Verificar se está rodando
docker-compose ps

# Ver logs
docker-compose logs api

# Testar manualmente
curl -v http://localhost:5000/health
```

### Confluence não acessa API
```bash
# Do container Confluence, testar:
curl http://host.docker.internal:5000/health
# Ou use IP do host em vez de localhost
```

### Dados não atualizam
```bash
# Verificar se webPosto API remota está acessível
docker-compose exec api curl -I http://web.qualityautomacao.com.br

# Testar sincronização
docker-compose exec api curl http://localhost:5000/sync/financeiro
```

---

## 📈 Monitoramento

### Ver métricas da API
```bash
docker stats webposto-api
```

### Ver logs em tempo real
```bash
docker-compose logs -f api
```

### Verificar banco de dados
```bash
docker-compose exec api sqlite3 webposto.db ".tables"
```

---

## 🔐 Segurança

**Para produção com Confluence:**

1. **Usar HTTPS**
   ```nginx
   server {
       listen 443 ssl;
       location / {
           proxy_pass http://localhost:5000;
       }
   }
   ```

2. **Autenticação**
   ```python
   # Adicionar headers de autenticação
   headers = {
       "Authorization": "Bearer seu-token-aqui"
   }
   ```

3. **CORS**
   ```python
   # Em src/main_minimal.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:8090"],
       allow_methods=["GET", "POST"],
   )
   ```

---

## 📝 Checklist de Integração

- [ ] API rodando em http://localhost:5000
- [ ] Confluence rodando em http://localhost:8090
- [ ] Teste: curl http://localhost:5000/health
- [ ] Teste: curl http://localhost:5000/sync/financeiro
- [ ] Plugin Python instalado em Confluence
- [ ] Webhook/macro configurado
- [ ] Sincronização automática (cron/scheduler)
- [ ] Monitoramento ativo

---

**Pronto para integração! 🚀**
