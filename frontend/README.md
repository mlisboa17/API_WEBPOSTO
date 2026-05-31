# 🚀 Frontend - WebPosto API Explorador

Dashboard interativo para explorar e testar a API WebPosto em desenvolvimento.

## 📋 O que é?

Um explorador visual completo que permite:
- ✅ Listar todos os **17 módulos de endpoints** disponíveis
- ✅ Testar requisições **GET, POST, PUT, DELETE** em tempo real
- ✅ Adicionar **query parameters** e **body JSON** dinamicamente
- ✅ Ver respostas formatadas com syntax highlighting
- ✅ Visualizar dados em cards ou JSON
- ✅ Monitorar status da API em tempo real

## 🚀 Como Usar

### 1. **Abrir o Frontend**
```bash
# Abra no navegador:
file:///c:/Users/mlisb/OneDrive/ProjetosAntigravy/LOGOS%20SPACE/Api_WebPosto/frontend/index.html

# Ou inicie um servidor local:
python -m http.server 5500 --directory frontend
# Acesse: http://localhost:5500/index.html
```

### 2. **Ter a API Rodando**
Certifique-se de que a API está online antes:
```bash
docker-compose up -d
# ou
python main.py
```

### 3. **Explorar Endpoints**
1. Na aba **"Explorador de Endpoints"**, veja a lista de todos os endpoints por módulo
2. Clique em um endpoint para selecioná-lo
3. O painel de teste aparecerá à direita

### 4. **Testar um Endpoint**
```
1. Selecione um endpoint (ex: GET /clientes)
2. Adicione query parameters se necessário (ex: ?limit=10)
3. Se POST/PUT, preench o body JSON
4. Clique em "✈️ Enviar Requisição"
5. Veja a resposta formatada abaixo
```

### 5. **Exemplo Prático**

**Listar Clientes:**
- Endpoint: `GET /clientes`
- Query: `?limit=10&offset=0`
- Resultado: Lista de clientes em JSON

**Criar Cliente:**
- Endpoint: `POST /clientes`
- Body:
```json
{
  "nome": "Novo Cliente",
  "email": "cliente@example.com",
  "telefone": "11-98765-4321"
}
```

## 🎨 Abas do Dashboard

### 1️⃣ **Explorador de Endpoints**
- Lista completa de endpoints organizados por módulo
- Preview rápido de cada endpoint
- Painel de teste integrado

### 2️⃣ **Visualizar Dados**
- Exibe dados em formato de cards
- Suporta paginação (mostra até 12 itens)
- Mostra resumo das principais propriedades

### 3️⃣ **Documentação**
- Guia de como usar o explorador
- Módulos disponíveis
- Configurações da API

## 📊 Módulos Disponíveis

| Módulo | Endpoints | Descrição |
|--------|-----------|-----------|
| 🛢️ **Abastecimento** | 3 | Combustível, divergências, encerrantes |
| 👥 **Clientes** | 3 | Dados cadastrais, frota, grupos |
| 📦 **Produtos** | 3 | Combustível, estoque, preços |
| 💰 **Financeiro** | 3 | Títulos receber/pagar, caixa, cartão |
| 📈 **Vendas** | 3 | Notas fiscais, pedidos, múltiplas filiais |
| 📋 **Auditoria** | 2 | Histórico de operações, relatórios |
| ⚙️ **Sistema** | 1 | Health check, status |

## 🔧 Configuração

### Base URL
```
http://localhost:8000
```

### Headers Automáticos
- `Content-Type: application/json`
- Para autenticação, adicione o token no endpoint desejado

### Cors
Certifique-se de que a API está configurada com CORS habilitado:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🎯 Casos de Uso Comuns

### 1. Testar Integração com WebPosto
```
1. Ir para "Explorador"
2. Selecionar GET /clientes
3. Enviar requisição
4. Confirmar que dados chegam corretamente
```

### 2. Validar Modelo de Dados
```
1. Ir para "Visualizar Dados"
2. Selecionar um endpoint
3. Ver se os campos retornam como esperado
```

### 3. Testar Criação de Dados
```
1. Selecionar POST /clientes
2. Preencher JSON com dados de teste
3. Enviar e verificar ID retornado
```

## 📱 Recursos

- ✅ **Responsivo**: Funciona em desktop, tablet e mobile
- ✅ **Sem Dependências**: Usa React via CDN
- ✅ **Zero Build**: Abra no navegador direto
- ✅ **Dark Mode Ready**: Interface moderna com gradientes
- ✅ **Status em Tempo Real**: Monitora saúde da API
- ✅ **Cópia Fácil**: Comande curl copiáveis

## 🐛 Troubleshooting

### "API Offline"
- Certifique-se de que a API está rodando: `curl http://localhost:8000/health`
- Verifique se o Docker está ativo: `docker ps`

### CORS Error
- Adicione middleware CORS na API FastAPI
- Ou configure proxy no frontend

### Endpoint não responde
- Verifique se o endpoint existe em `main.py`
- Veja logs: `docker logs api-webposto`

## 📚 Próximos Passos

1. ✅ Use este frontend para explorar os 51 endpoints
2. ✅ Identifique quais você vai usar no seu projeto
3. ✅ Faça testes com dados reais
4. ✅ Documente os endpoints essenciais
5. ✅ Implemente no seu app

## 🚀 Deploy

Para deploy em produção:
```bash
# Copie os arquivos para seu servidor web
cp frontend/index.html /var/www/api-explorer/
cp frontend/*.css /var/www/api-explorer/
cp frontend/*.js /var/www/api-explorer/

# Ou use Docker
docker run -p 80:80 -v $(pwd)/frontend:/usr/share/nginx/html nginx
```

---

**Desenvolvido com ❤️ para o projeto WebPosto API**
