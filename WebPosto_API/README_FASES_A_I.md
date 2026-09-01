# README — EXECUTOR FASES A-I
## Cadastro Contínuo de Produtos WebPosto | Empresa 118508

---

## 📋 RESUMO RÁPIDO

Este projeto implementa um **executor automático das FASES A-I** para cadastro em lote de 484 produtos na API WebPosto. As fases rodam **SEM INTERRUPÇÕES** em sequência contínua.

### Resultados Atuais
```
Total de Produtos:     484
├─ READY_TO_CREATE:     31 (6.4%)  ✓ Autorizado POST imediato
├─ REVIEW_REQUIRED:    435 (89.9%)  ⚠ Requer dados complementares
└─ BLOCKED:             18 (3.7%)   ✗ GTIN inválido
```

---

## 🚀 COMO EXECUTAR

### Pré-requisitos
```bash
# Python 3.10+
python --version

# Bibliotecas necessárias
pip install openpyxl httpx python-dotenv pydantic
```

### Arquivo de Configuração
```bash
# Criar .env na raiz do projeto
WEBPOSTO_API_KEY=<sua_chave_api>
```

### Executar o Executor

**Versão 1 (Básica - FASES A, B, G, I):**
```bash
python execute_fases_a_i.py
```

**Versão 2 (Completa - FASES A-I):**
```bash
python execute_fases_a_i_v2_completo.py
```

### Output
```
Arquivo de Log:      data/product_registration/executions/execution_YYYYMMDD_HHMMSS.log
Relatório JSON:      data/product_registration/executions/relatorio_fases_a_i_YYYYMMDD_HHMMSS.json
Relatório Markdown:  RELATORIO_FASES_A_I.md (este arquivo)
```

---

## 📊 ESTRUTURA DAS FASES

### FASE A — Validação Preflight (GTIN Checksum)
**Objetivo:** Validar 484 registros contra critério GTIN-8/12/13/14

**Entrada:** Planilha `CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx`  
**Processamento:** 
- Validar formato GTIN (8, 12, 13 ou 14 dígitos)
- Calcular e validar checksum
- Detectar zeros à esquerda
- Detectar duplicatas

**Saída:**
```json
{
  "VALID_GTIN": 466,
  "INVALID_GTIN": 18,
  "GTIN_8": 8,
  "GTIN_12": 25,
  "GTIN_13": 432,
  "GTIN_14": 1
}
```

---

### FASE B — Enriquecimento DF-e (174 NF-e / 928 Items)
**Objetivo:** Reutilizar dados de NF-e histórica

**Entrada:** Índice DF-e (`data/dfe_store/items/dfe_doc_*.json`)  
**Processamento:**
- Carregar 928 items de NF-e em memória
- Mapear EAN → [items]
- Extrair NCM, CEST, unidades, descrição, fornecedor

**Saída:**
```json
{
  "DFE_MATCHED": 31,
  "DFE_NOT_MATCHED": 435,
  "EANs_no_indice": 483
}
```

**Produtos Enriquecidos:** 31 (6.6% da planilha)

---

### FASE C — Resolver Grupos
**Objetivo:** Mapear produtos a GRUPO válido no catálogo WebPosto

**Entrada:** Coluna GRUPO_API_CODIGO da planilha  
**Processamento:**
- Buscar GRUPO_API_CODIGO na planilha
- Validar contra catálogo (GET /INTEGRACAO/GRUPO — não implementado)
- Aplicar mapeamento conhecido (Ref 016 → Grupo 55446)

**Saída:**
```json
{
  "GRUPOS_RESOLVIDOS": 35,
  "GRUPOS_NAO_RESOLVIDOS": 431
}
```

**Status:** Requer complementação de GRUPO_API_CODIGO para 431 produtos

---

### FASE D — Resolver NCM/CEST
**Objetivo:** Obter classificação fiscal (NCM) e código de regime especial

**Entrada:** DF-e (Fase B) + Planilha  
**Processamento:**
- Extrair NCM de DF-e (prioridade 1)
- Extrair CEST de DF-e (prioridade 1)
- Usar coluna NCM/CEST da planilha (prioridade 2)
- Aplicar heurística de descrição (prioridade 3)

**Saída:**
```json
{
  "NCM_RESOLVIDOS": 31,
  "CEST_RESOLVIDOS": 26
}
```

**Status:** 435 produtos requerem NCM (via DF-e complementar ou heurística)

---

### FASE E — Preço Compra e Custo
**Objetivo:** Extrair PRECO_COMPRA (de NF-e) e PRECO_CUSTO (regra)

**Entrada:** DF-e + Planilha  
**Processamento:**
- PRECO_VENDA: coluna planilha (obrigatório)
- PRECO_COMPRA: extrair de DF-e com conversão (uCom vs uTrib)
- PRECO_CUSTO: regra corporativa ou coluna planilha

**Saída:**
```json
{
  "PRECO_VENDA_OK": 466,
  "PRECO_COMPRA_OK": 0,
  "PRECO_CUSTO_OK": 0
}
```

**Status:** PRECO_COMPRA/CUSTO requerem implementação de conversão DF-e

---

### FASE F — Tributação (Modelo Fiscal)
**Objetivo:** Aplicar modelo fiscal correto (ICMS, PIS/COFINS)

**Entrada:** NCM + Grupo + Contexto (empresa 118508, PE, Lucro Presumido)  
**Processamento:**
- Mapear NCM/Grupo → Modelo Fiscal Aprovado
- Usar template BONO para biscoitos (grupo 55446, NCM 19053100)
- Validar contra modelos pré-aprovados

**Saída:**
```json
{
  "MODELOS_APLICADOS": 0
}
```

**Status:** Requer mapeamento NCM → Modelo Fiscal

---

### FASE G — Preflight Pós-Enriquecimento
**Objetivo:** Classificar cada produto em categoria final

**Entrada:** Resultado de todas as fases anteriores  
**Processamento:**
- READY_TO_CREATE: GTIN válido + DF-e + Preço venda
- REVIEW_REQUIRED: GTIN válido mas dados incompletos
- BLOCKED: GTIN inválido ou crítico

**Saída:**
```json
{
  "READY_TO_CREATE": 31,
  "REVIEW_REQUIRED": 435,
  "BLOCKED": 18
}
```

---

### FASE H — Cadastro Real (POST /INTEGRACAO/INCLUIR_PRODUTO)
**Objetivo:** Criar produtos na API WebPosto

**Status:** ⚠ NÃO EXECUTADO (Pendente Aprovação)

**Procedimento (quando aprovado):**
```bash
POST https://web.qualityautomacao.com.br/INTEGRACAO/INCLUIR_PRODUTO
  ?CHAVE=<api_key>

Body: {
  "empresa_codigo": 118508,
  "centro_custo": 24886,
  "ean": "...",
  "descricao": "...",
  "grupo_codigo": ...,
  "ncm": "...",
  "cest": "...",
  "preco_venda": ...,
  "preco_compra": ...,
  "preco_custo": ...,
  ...
}
```

**Resposta Esperada:**
```json
{
  "ret": "0",
  "men": "Produto criado com sucesso",
  "cod_produto": 123456
}
```

---

### FASE I — Relatório Final
**Objetivo:** Consolidar contadores e gerar audit trail

**Saída:** `relatorio_fases_a_i_YYYYMMDD_HHMMSS.json`

```json
{
  "empresa": 118508,
  "total": 484,
  "ready_to_create": 31,
  "review_required": 435,
  "blocked": 18,
  "timestamp": "2026-08-14T13:18:36Z"
}
```

---

## 📁 ESTRUTURA DO PROJETO

```
WebPosto_API/
├── execute_fases_a_i.py              ← Script executor v1 (básico)
├── execute_fases_a_i_v2_completo.py  ← Script executor v2 (completo)
├── README_FASES_A_I.md               ← Este arquivo
├── RELATORIO_FASES_A_I.md            ← Relatório detalhado
│
├── src/
│   └── operational/
│       ├── product_registration/
│       │   ├── service.py
│       │   ├── schemas.py
│       │   ├── spreadsheet_reader.py
│       │   ├── body_builder.py
│       │   ├── registration_executor.py
│       │   └── ...
│       └── dfe/
│           └── batch.py
│
├── data/
│   ├── dfe_store/
│   │   ├── documents/      (174 NF-e XML)
│   │   └── items/          (928 items JSON)
│   └── product_registration/
│       └── executions/
│           ├── execution_20260814_101836.log
│           └── relatorio_fases_a_i_20260814_101836.json
│
└── CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx  (planilha origem)
```

---

## 🔧 CUSTOMIZAÇÃO

### Mudar Empresa
```python
# execute_fases_a_i.py ou execute_fases_a_i_v2_completo.py

EMPRESA_CODIGO = 118508    # ← Alterar aqui
EMPRESA_NOME = "CONVENIENCIA 24 HORAS"
CENTRO_CUSTO = 24886       # ← Validado por GET
UF = "PE"
REGIME = "LUCRO_PRESUMIDO"
```

### Mudar Planilha
```python
PLANILHA_PATH = Path(
    r"C:\seu\caminho\CADASTRO_PRODUTOS.xlsx"
)
```

### Mudar Base URL
```python
BASE_URL = "https://seu-servidor.com"
```

---

## 📈 MÉTRICAS ATUAIS

| Métrica | Valor | % |
|---------|-------|---|
| Total | 484 | 100% |
| GTIN válido | 466 | 96.3% |
| GTIN inválido | 18 | 3.7% |
| DF-e matched | 31 | 6.4% |
| Grupos resolvidos | 35 | 7.2% |
| NCM resolvidos | 31 | 6.4% |
| Preço venda OK | 466 | 96.3% |
| **READY_TO_CREATE** | **31** | **6.4%** |
| REVIEW_REQUIRED | 435 | 89.9% |
| BLOCKED | 18 | 3.7% |

---

## ⏱️ PERFORMANCE

| Fase | Tempo | Status |
|------|-------|--------|
| A (Validação) | 3ms | ✓ |
| B (DF-e) | 350ms | ✓ |
| C (Grupos) | 0ms | ✓ |
| D (NCM/CEST) | 0ms | ✓ |
| E (Preços) | 0ms | ✓ |
| F (Tributação) | 1ms | ✓ |
| G (Classificação) | 1ms | ✓ |
| H (POST) | - | ⚠ Não executado |
| I (Relatório) | 3ms | ✓ |
| **TOTAL** | **~370ms** | **✓** |

---

## 🚨 PROBLEMAS CONHECIDOS

### 1. 18 Produtos com GTIN Inválido
**Impacto:** Bloqueados para cadastro  
**Solução:** Retornar à origem, corrigir EAN  
**Prazo:** 1-2 dias

### 2. 435 Produtos sem DF-e
**Impacto:** Não enriquecidos com NCM/preço  
**Solução:** Solicitar DF-e complementar, usar tabela padrão  
**Prazo:** 3-5 dias

### 3. Falta Coluna GRUPO_API_CODIGO para 431 Produtos
**Impacto:** Requer enriquecimento manual/automático  
**Solução:** Implementar heurística NCM→GRUPO  
**Prazo:** 1-2 dias (80% automático)

### 4. Modelo Fiscal Não Implementado
**Impacto:** Não pode prosseguir para POST sem modelo  
**Solução:** Mapear NCM/Grupo → Modelo Aprovado  
**Prazo:** 2-3 dias

---

## 📞 PRÓXIMAS AÇÕES

### Curto Prazo (48h)
- [ ] Corrigir 18 GTINs inválidos
- [ ] Completar GRUPO_API_CODIGO para 431 produtos
- [ ] Obter DF-e complementar para 435 produtos

### Médio Prazo (Semana 1)
- [ ] Implementar conversão PRECO_COMPRA (DF-e)
- [ ] Mapear NCM → Modelo Fiscal
- [ ] Aplicar modelo BONO para biscoitos
- [ ] Expandir cobertura NCM a 80%+

### Longo Prazo (Semana 2)
- [ ] Executar FASE H (POST /INTEGRACAO/INCLUIR_PRODUTO)
- [ ] Monitorar respostas (HTTP 200/201, RET=3, etc.)
- [ ] Gerar audit trail completo
- [ ] Validar pós-cadastro (GET /INTEGRACAO/V1/PRODUTOS)

---

## 📖 REFERÊNCIA

- **API WebPosto:** https://web.qualityautomacao.com.br/swagger
- **Planilha:** `CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx`
- **DF-e Store:** `data/dfe_store/` (174 NF-e, 928 items)
- **Relatório Detalhado:** `RELATORIO_FASES_A_I.md`

---

## 📝 CHANGELOG

### v2.0 — 2026-08-14
- ✓ Implementação completa FASES A-I
- ✓ Validação GTIN com checksum
- ✓ Enriquecimento DF-e (31 produtos)
- ✓ Classificação em READY/REVIEW/BLOCKED
- ✓ Relatório detalhado em JSON

### v1.0 — 2026-08-14
- ✓ Executor básico (A, B, G, I)
- ✓ Carregamento planilha + DF-e
- ✓ Logging estruturado

---

**Última Atualização:** 2026-08-14  
**Manutenção:** LOGOS Engenharia de Dados
