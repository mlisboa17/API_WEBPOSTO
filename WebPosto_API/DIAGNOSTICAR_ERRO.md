# 🔍 Diagnóstico de Erros na API

## Erro Atual: "Method Not Allowed" (405)

### ✅ Passo 1: Testar Endpoints Diretos

Execute no PowerShell:
```powershell
.\TESTAR_ENDPOINTS.ps1
```

**Resultado esperado:**
- ✅ Health: 200 OK
- ✅ Listar Financeiro: 200 OK
- ✅ Listar Caixa: 200 OK
- ✅ Listar Auditoria: 200 OK

---

### 🌐 Passo 2: Verificar Console do Navegador

1. Abra um dos dashboards (admin-dashboard.html)
2. Pressione **F12** ou **Clique Direito → Inspecionar**
3. Vá para aba **Console**
4. Procure por erros em vermelho

**O que procurar:**
- Mensagens de erro de fetch (red text)
- Status code 405, 404, 500, etc
- CORS errors

**Copie e cole aqui a mensagem de erro exata**

---

### 🔗 Passo 3: Verificar a URL Exata

Na aba **Network** (F12):
1. Recarregue a página (F5)
2. Procure por requisições para `api/v1`
3. Clique em cada uma
4. Verifique:
   - **Method:** GET, POST, etc
   - **URL:** Caminho completo
   - **Status:** 200, 405, 404, etc
   - **Response:** Ver a resposta do servidor

---

### 📋 Checklist de Verificação

- [ ] API está rodando (`http://localhost:5000/health` acessível)?
- [ ] Console do navegador mostra erros? (F12 → Console)
- [ ] Network mostra qual URL está falhando? (F12 → Network)
- [ ] O método HTTP está correto (GET vs POST)?
- [ ] A porta é 5000 (não 8000)?

---

### 💡 Causas Comuns do Erro 405

| Erro | Causa | Solução |
|------|-------|---------|
| GET /api/v1 → 405 | Endpoint não existe | Usar `/api/v1/financeiro` não `/api/v1` |
| POST /api/v1/financeiro → 405 | Método não permitido | Verificar se endpoint aceita POST |
| /sync/financeiro → 405 | Rota conflitante | Router CRUD pode estar bloqueando |

---

### 🎯 Próximo Passo

**Responda:**
1. Executou `TESTAR_ENDPOINTS.ps1`? O que viu?
2. Abriu F12 → Console? Quais erros apareceram?
3. Abriu F12 → Network? Qual URL está falhando?

Com essas informações, vou corrigir o problema! 🚀
