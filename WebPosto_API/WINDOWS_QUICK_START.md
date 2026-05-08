# 🪟 webPosto API — Windows Quick Start

**Status:** ✅ Pronto para rodar

---

## 🚀 Iniciar em 3 Passos

### **Opção A: Batch File (Mais Simples)**

```bash
# Duplo-clique em RUN_API_WINDOWS.bat
# OU execute no Command Prompt:
RUN_API_WINDOWS.bat
```

### **Opção B: PowerShell (Recomendado)**

```powershell
# Execute no PowerShell (como administrador é melhor):
powershell -ExecutionPolicy Bypass -File RUN_API_WINDOWS.ps1

# OU simplesmente:
.\RUN_API_WINDOWS.ps1
```

### **Opção C: Manual (Controle Total)**

```powershell
# 1. Abrir PowerShell na pasta do projeto
# Dica: Shift + Clique direito na pasta > "Abrir PowerShell aqui"

# 2. Instalar dependências (primeira vez apenas)
pip install fastapi uvicorn pydantic sqlalchemy httpx tenacity pydantic-settings aiosqlite --break-system-packages

# 3. Rodar a API
python -m uvicorn src.main_minimal:app --host 0.0.0.0 --port 5000 --reload

# Resultado esperado:
# INFO:     Uvicorn running on http://0.0.0.0:5000
# INFO:     Application startup complete
```

---

## ✅ Verificar se Tá Funcionando

### **1️⃣ Health Check**
```
http://localhost:5000/health
```
**Resposta esperada:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "webposto_api": "http://web.qualityautomacao.com.br",
  "empresa": "POSTO VIP - Rio Doce",
  "cors": "enabled"
}
```

### **2️⃣ Abrir Dashboards**

| Dashboard | URL |
|-----------|-----|
| **Admin** (CRUD) | `admin-dashboard.html` |
| **Vendas** (Relatórios) | `vendas-dashboard.html` |
| **Diagnóstico** (Testes) | `diagnostico.html` |

**Dica:** Abra os arquivos `.html` diretamente no navegador.

### **3️⃣ Swagger API (Opcional)**
```
http://localhost:5000/docs
```

---

## 🆘 Troubleshooting Windows

### **Erro: "Access is denied"**
- PowerShell como **administrador**
- OU use o Batch file (`RUN_API_WINDOWS.bat`)

### **Erro: "ModuleNotFoundError: No module named 'src'"**
✅ **RESOLVIDO:** Criamos `src/__init__.py`

Se persistir:
```powershell
# Certifique-se que está na pasta CORRETA
cd "C:\Users\...\WebPosto_API"
ls src\main_minimal.py  # Deve listar o arquivo
```

### **Erro: "port 5000 is already in use"**
```powershell
# Localizar processo na porta 5000
netstat -ano | findstr :5000

# Matar processo (substitua PID)
taskkill /PID 12345 /F
```

### **Erro: "The system cannot find the path specified"**
- Use **Shift + Clique direito** na pasta → "Abrir PowerShell aqui"
- Ou copie o caminho completo com **aspas**:
```powershell
cd "C:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API"
```

### **Erro: "Failed to fetch" nos Dashboards**
1. ✅ API está rodando? (`http://localhost:5000/health`)
2. ✅ Porta 5000 aberta? (não há firewall bloqueando)
3. ✅ Diagnostico passou? (abra `diagnostico.html`)

---

## 📁 Arquivos Críticos

```
WebPosto_API/
├── src/
│   ├── __init__.py          ← NOVO (vai resolver ModuleNotFoundError)
│   ├── main_minimal.py      ← App principal
│   ├── models.py            ← Validações
│   └── crud.py              ← Lógica CRUD
├── RUN_API_WINDOWS.bat      ← NOVO (duplo-clique para rodar)
├── RUN_API_WINDOWS.ps1      ← NOVO (PowerShell script)
├── .env                     ← Configurações (não mexer)
├── admin-dashboard.html     ← CRUD Web UI
├── vendas-dashboard.html    ← Relatórios + Filtros
└── diagnostico.html         ← Teste de conexão
```

---

## 🎯 Próximos Passos

1. ✅ Rodar: `RUN_API_WINDOWS.bat` ou `.\RUN_API_WINDOWS.ps1`
2. ✅ Abrir: `admin-dashboard.html` no navegador
3. ✅ Testar: Criar um título (Financeiro)
4. ✅ Validar: Ver dados aparecerem
5. ✅ Explorar: `vendas-dashboard.html` com filtros

---

## 💡 Dicas Windows

**Atalho para abrir PowerShell na pasta:**
1. Abra a pasta `WebPosto_API` no Windows Explorer
2. Pressione **Shift + Clique direito** em espaço vazio
3. Selecione "Abrir PowerShell aqui" (ou "Open in Terminal")
4. Cole: `pip install fastapi uvicorn pydantic sqlalchemy httpx tenacity pydantic-settings aiosqlite --break-system-packages`
5. Cole: `python -m uvicorn src.main_minimal:app --port 5000 --reload`
6. Abra `http://localhost:5000/health` no navegador

**OU simplesmente duplo-clique em `RUN_API_WINDOWS.bat`** 👈 **MAIS FÁCIL!**

---

**Status:** Pronto! Rode `RUN_API_WINDOWS.bat` e aproveita. 🚀
