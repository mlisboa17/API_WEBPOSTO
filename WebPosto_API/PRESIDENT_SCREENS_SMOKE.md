# Smoke tests — 3 Telas do Presidente (porta 8046)

Runtime local: `http://127.0.0.1:8046`  
SPA: `http://127.0.0.1:8046/app/financial`

Substitua `DATA_INI` e `DATA_FIM` (YYYY-MM-DD) e, se necessário, `EMPRESA` (código WebPosto ou omita para rede).

## 1. Autenticação (obrigatório)

```bash
curl -s -c cookies.txt -X POST "http://127.0.0.1:8046/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"SEU_EMAIL\",\"password\":\"SUA_SENHA\"}"
```

Extraia o token para chamadas com Bearer (opcional — cookie também funciona):

```bash
TOKEN=$(grep access_token cookies.txt | awk '{print $7}')
```

## 2. Tela 1 — Owner Action Center

### Top 5 decisões

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/owner-action-center/top5?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

### Business health (score da rede)

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/owner-action-center/business-health?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

Esperado: `overall_score`, `status`, `deductions[]`.

## 3. Tela 2 — Cockpit Comercial (combustível)

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/fuel/executive?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

Esperado: `paridadePrecos[]` com `precoMedioCompra`, `precoMedioVenda`, `margemRealizadaPct`.

Snapshot (preferir — evita recomputo):

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/fuel/snapshot?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

## 4. Tela 3 — DRE & Fluxo de Caixa

### DRE gerencial

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/dre?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

Esperado: `faturamentoBruto`, `margemContribuicao`, `despesasOperacionais`, `porFilial`.

### Fluxo de caixa

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/finance/cash-flow?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

Esperado: `semanticBreakdown.despesas`, `semanticBreakdown.receitas`, `cards.saldoProjetado`.

Snapshot agregado executivo (DRE + KPIs — uma única chamada):

```bash
curl -s -b cookies.txt -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8046/api/v1/executive/snapshot?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=EMPRESA"
```

## 5. Filial fora do escopo (deve retornar 403)

```bash
curl -s -o /dev/null -w "%{http_code}\n" -b cookies.txt \
  "http://127.0.0.1:8046/api/v1/owner-action-center/business-health?dataInicial=DATA_INI&dataFinal=DATA_FIM&empresaCodigo=99999999"
```

Esperado: `403` — frontend exibe *"Dados indisponíveis para esta filial"*.

## 6. Testes automatizados (pytest)

```bash
cd WebPosto_API
python -m pytest tests/integration/test_president_screens_api.py -v
```

## 7. Verificação visual rápida (SPA)

| Tela | URL |
|------|-----|
| Owner / Diretoria | `/app/financial?view=owner-diretoria` |
| Combustível | `/app/financial?view=fuels` |
| Fluxo de caixa | `/app/financial?view=treasuryHub` (aba Fluxo) |
