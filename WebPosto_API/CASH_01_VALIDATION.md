# CASH-01 Validation — Exposição de Fechamento de Caixa

## 1. Implementation

Camada fina de orquestração sobre a conferência D02 existente:

- Service: `src/services/cash_reconciliation/cash_exposure_service.py`
- API: `GET /api/v1/cash-reconciliation/cash-exposure`
- UI: bloco na view legado `frontend/pages/cashReconciliation.js` (Conferência Financeira)
- Testes: `tests/unit/test_cash_exposure_service.py`

**Não** cria FinancialFinding, migrations, Money Hunter genérico, EDI, OFX novo ou Expense Hunter.

## 2. Reuse

| Componente | Uso |
|------------|-----|
| `CashReconciliationService.build_items` | Ingestão CAIXA / CAIXA_APRESENTADO |
| `PreReconciliationEngine` | Alinha valorEsperado/valorRealizado |
| `expected_realized()` (`nature_strategies`) | Regra DINHEIRO (apurado − sangria) e demais naturezas |
| `PaymentNatureCode` | Breakdown DINHEIRO / CARTAO / PIX |
| Rota prefix `/api/v1/cash-reconciliation` | Extensão HTTP mínima |
| UI Conferência Financeira | Superfície existente |

## 3. Calculation

Registrado na pré-implementação e no payload `sources`:

| Campo | Origem |
|-------|--------|
| **EXPECTED** | `expected_realized(item)` ou `valorApurado` (mesmo domínio do PreEngine) |
| **IDENTIFIED** | `valorRealizado` ou `valorApresentado` (apresentado no fechamento) |
| **EXPOSURE** | `expected_amount − identified_amount` (positivo = curto no fechamento) |
| **BREAKDOWN** | Agregação por lane: DINHEIRO, CARTAO, PIX (`TRANSFERENCIA_CREDITO` + `PRE_PAGO`) |

Lanes excluídos do total: DESPESA, VALES, EMPRÉSTIMO, CHEQUES, etc. (não são “recebimento esperado” no sentido CASH-01).

## 4. Data Scope

| Lane | data_scope | Significado |
|------|------------|-------------|
| Total | `CASH_CLOSING` | Batimento de fechamento de caixa |
| DINHEIRO | `CASH_CLOSING` | Apurado vs apresentado (após sangria na expectativa) |
| CARTAO | `CASH_CLOSING` | Apurado vs apresentado no caixa — **não** EDI/banco |
| PIX | `AGGREGATED_CASH_DATA` | Agregado VFP/caixa; **sem** correlação tx venda↔banco |

**Não interpretar como `BANK_SETTLED`.**

## 5. Tests

```bash
# worktree CASH01
python -m pytest tests/unit/test_cash_exposure_service.py \
  tests/unit/test_cash_reconciliation_service.py \
  tests/unit/test_prestacao_contas_parser.py \
  tests/unit/test_financial_review_inbox.py \
  -o addopts= -q
```

Resultado executado no worktree limpo (pré-live):

```
22 passed, 32 warnings (deprecations Pydantic não relacionadas)
test_cash_exposure_service.py + test_cash_reconciliation_service.py + test_financial_review_inbox.py
test_prestacao_contas_parser.py: ABSENT neste HEAD (33a880a)
```

Re-run pós-live (2026-07-31 worktree; venv compartilhado sem `asyncpg`):

```
test_cash_exposure_service.py + test_cash_reconciliation_service.py → 13 passed
test_financial_review_inbox.py → ERROR collection (ModuleNotFoundError: asyncpg) — ambiente, não regressão CASH-01
```

## 6. Live Evidence (histórico)

`LIVE_VALIDATION_PENDING` — substituído pela seção **LIVE FINANCIAL VALIDATION** abaixo.

## 7. False Positive Risks

Exposição **não** significa perda confirmada. Pode ser:

- timing (sangria/depósito D+1);
- erro de digitação no apresentado;
- pendência de conferência;
- diferença operacional;
- PIX/cartão só no caixa (ainda não no banco).

## 8. Known Limitations

- Sem EDI adquirente / OFX match nesta sprint.
- PIX sem identificador transacional.
- Breakdown só para lanes com movimento; demais = `UNKNOWN`.
- Financial Review bridge **adiado** (requer novo `request_type` ≠ `NOMINAL_IDENTIFICATION_REVIEW`).
- UI apenas no frontend legado de Conferência (executive-web `/financial/reconciliation` não existe neste HEAD `33a880a`).

## 9. Technical Debt (próximo sprint)

1. Expor HTTP do matching cartão×OFX (CASH-02) — lib já existe.
2. Bridge FIN com `request_type` adequado + assign.
3. Validação live documentada com evidência real.

## 10. Product Gate (pré-live)

**READY_FOR_USER_VALIDATION** (unit-only; superseded pela gate live abaixo).

---

## LIVE FINANCIAL VALIDATION

Validation date: 2026-07-31  
Branch: `feature/cash-01-exposure`  
HEAD: `33a880ad3bbfbf4a230843ada2fabe1363601185`  
Worktree: `C:/Users/mlisb/OneDrive/ProjetosAntigravy/LOGOS SPACE/Api_WebPosto_CASH01_CLEAN`  
Artifact: `WebPosto_API/tmp_cash01_live_validation.json` (read-only WebPosto via script; sem write no ERP)

### Empresa / Period / Source

| Campo | Valor |
|-------|-------|
| Empresa | **11495 — POSTO VIP** (não Casa Caiada) |
| Period | **2026-08-10 .. 2026-08-10** |
| Real data source | WebPosto live: CAIXA / CAIXA_APRESENTADO / VFP (HTTP 200), `caixaTurnos=2`, `vfpRows=178`, `sangriaTotal_meta=0` |

### Totals (endpoint CASH-01)

| Metric | Value (R$) |
|--------|------------|
| EXPECTED | 20.559,62 |
| IDENTIFIED | 33.589,15 |
| EXPOSURE | **−13.029,53** (OVER / identified > expected) |

### Breakdown

| Lane | expected | identified | exposure | data_scope |
|------|----------|------------|----------|------------|
| CARTAO | 2.637,98 | 17.026,69 | **−14.388,71** | CASH_CLOSING |
| DINHEIRO | 7.178,18 | 5.819,00 | **+1.359,18** | CASH_CLOSING |
| PIX | 10.743,46 | 10.743,46 | 0,00 | AGGREGATED_CASH_DATA |

### Product review (Fase 1)

**CASH-01 pode afirmar (com dados atuais):**

- Há divergência aritmética entre um “esperado” derivado de `expected_realized`/`valorApurado` e um “identificado” derivado de `valorRealizado`/`valorApresentado` nas lanes DINHEIRO/CARTAO/PIX do fechamento.
- Sinal: exposure > 0 = short; < 0 = over; = 0 = compatível **nessa fórmula**.

**CASH-01 NÃO pode afirmar:**

- `BANK_SETTLED`, `CONFIRMED_LOSS`, `FRAUD`, `MISSING_MONEY`, `RECOVERED_VALUE`.
- Liquidação de cartão/adquirente ou conciliação PIX bancária.
- Que a exposição CARTÃO do live seja um gap real de fechamento (ver blocker).

**Risco de nomenclatura:** “Exposição” pode ser lida como perda. Disclaimer da API ajuda, mas o número CARTÃO (−14k) induz pânico falso. Nomes expected/identified/exposure são adequados **só se** ambos lados forem CASH_CLOSING gross; hoje CARTÃO mistura semânticas.

### Architecture review (Fase 2)

Reuse confirmado: `build_items` → `PreReconciliationEngine` → `expected_realized` → `PaymentNatureCode` → HTTP cash-reconciliation → UI Conferência.

`cash_exposure_service.py` continua camada fina de composição.

**Duplicação / fork semântico documentado (não refatorado):**

- D02 `natureTotals` / `item.diferenca` batem **gross** apurado×apresentado (CARTAO ap=au=17.026,69; preCheck `divergentAmount`=1.359,18 = só DINHEIRO).
- CASH-01 usa `expected_realized` para EXPECTED; para CARTAO isso vira **soma de `expectedNet` do `cardBreakdown` agregado do período**, anexado **igual** a cada item CARTAO de turno (`build_items` linhas ~331–342).
- Resultado: expected CARTAO = 1.318,99 × 2 turnos = 2.637,98 vs identified gross 17.026,69.

### Source trace (Fase 6)

**DINHEIRO** (2 turnos)

| Campo | Evidência |
|-------|-----------|
| SOURCE RECORDS | `11495:4403082:DINHEIRO`, `11495:4403155:DINHEIRO` |
| valorApurado | 924,45 + 6.253,73 = **7.178,18** |
| valorApresentado | 0,00 + 5.819,00 = **5.819,00** |
| valorRealizado | = apresentado (PreEngine) **5.819,00** |
| sangria | `null` em ambos; meta `sangriaTotal=0` |
| EXPECTED SOURCE | `expected_realized` = apurado − 0 → **7.178,18** |
| IDENTIFIED SOURCE | valorRealizado/apresentado → **5.819,00** |
| RESULT | exposure **+1.359,18** |

**CARTAO** (2 turnos) — **BLOCKER**

| Campo | Evidência |
|-------|-----------|
| SOURCE RECORDS | `11495:4403082:CARTAO`, `11495:4403155:CARTAO` |
| valorApurado | 1.446,46 + 15.580,23 = **17.026,69** (= natureTotals.au) |
| valorApresentado / Realizado | **17.026,69** (fechamento bate; `diferenca` item = 0) |
| EXPECTED SOURCE | `expected_realized` → sum(`cardBreakdown.expectedNet`) **período** = **1.318,99** **colado em cada turno** → soma CASH-01 **2.637,98** |
| IDENTIFIED SOURCE | gross apresentado/realizado **17.026,69** |
| RESULT | exposure **−14.388,71** — **não** é gap de fechamento D02 |

**PIX** (`TRANSFERENCIA_CREDITO`, agregado)

| Campo | Evidência |
|-------|-----------|
| SOURCE RECORDS | 2 itens; ap=ap=re= **10.743,46** |
| EXPECTED / IDENTIFIED | ambos apurado/apresentado |
| RESULT | exposure **0**; scope `AGGREGATED_CASH_DATA` — **não** bank settle |

### Expected semantics (Fase 7)

| Lane | Classificação | Evidência |
|------|---------------|-----------|
| DINHEIRO | **VALID** (com ressalva) | apurado vs apresentado é o batimento de caixa; regra sangria **não exercitada** no live (`sangria=None` sempre em `build_items`). Sem double-count de sangria neste dia. |
| CARTAO | **INVALID** para CASH-01 | expected = MDR/net VFP agregado, não valorApurado de fechamento; ainda **duplicado por turno**. |
| PIX | **VALID** como agregado caixa | expected = valorApurado; ok para batimento agregado, não para banco. |

**EXPECTED SEMANTICS (global CASH-01):** **INVALID** — contaminado pelo CARTÃO.

### Identified semantics (Fase 8)

| Lane | Classificação | Nota |
|------|---------------|------|
| DINHEIRO | **VALID** | apresentado/realizado = o que o operador informou no fechamento; turno com apresentado=0 é gap operacional/digitação, não bug de campo. |
| CARTAO | **VALID** como gross de caixa | valorRealizado≈apresentado≈apurado = fechamento; **não** liquidação adquirente. |
| PIX | **QUESTIONABLE** | agregado; zero exposure ≠ PIX conciliado no banco. |

**IDENTIFIED SEMANTICS (global):** **QUESTIONABLE** — identified CARTÃO é ok; o par expected×identified no CARTÃO é semanticamente quebrado.

### Manual reproduction (Fase 9)

| Lane | expected | identified | manual exposure | endpoint | MATCH |
|------|----------|------------|-----------------|----------|-------|
| DINHEIRO | 7178,18 | 5819,00 | 1359,18 | 1359,18 | YES |
| CARTAO | 2637,98 | 17026,69 | −14388,71 | −14388,71 | YES (aritmética) |
| PIX | 10743,46 | 10743,46 | 0 | 0 | YES |
| TOTAL | 20559,62 | 33589,15 | −13029,53 | −13029,53 | YES |

Aritmética bate; **semântica financeira do CARTÃO falha**.

### Total reconciliation (Fase 10)

SUM(lanes expected/identified/exposure) = totais do DTO → **EXACT**  
(Não há arredondamento oculto; lanes fora do breakdown não entram no total CASH-01.)

### Signal test (Fase 11)

- SHORT real: DINHEIRO +1.359,18 (expected > identified) — visível.
- OVER real no payload: CARTÃO/total negativos — **visíveis**, mas OVER do CARTÃO é **falso positivo semântico** (não sobra de caixa).
- Testes unitários cobrem sinal; evidência live do OVER “bom” não isolada sem o bug CARTÃO.

### False-positive analysis (Fase 12) — divergências

**DINHEIRO +1.359,18**

| Hipótese | Rating |
|----------|--------|
| DIGITATION / apresentado zerado em 1 turno | POSSIBLE |
| PARTIAL_CLOSING | POSSIBLE |
| REAL_CLOSING_DIFFERENCE | POSSIBLE |
| SANGRIA | UNLIKELY (meta 0; sangria null) |
| ESTORNO / TIMING / LATE_POSTING | UNKNOWN |
| FRAUDE/PERDA | **não concluir** |

**CARTAO −14.388,71**

| Hipótese | Rating |
|----------|--------|
| DATA_QUALITY / regra expectedNet vs gross | **POSSIBLE** (causa raiz) |
| CARD_SETTLEMENT_TIMING | POSSIBLE como *interpretação errada* do número |
| REAL_CLOSING_DIFFERENCE | **UNLIKELY** (D02 ap=au; diferenca=0) |

**PIX 0**

| Hipótese | Rating |
|----------|--------|
| PIX_AGGREGATION masquerading as settled | POSSIBLE |
| REAL bank match | UNLIKELY sem OFX |

### Confidence by lane (Fase 13)

| Lane | Confidence | Reason |
|------|------------|--------|
| DINHEIRO | **MEDIUM** | Fonte de fechamento reconciliável; sangria não validada em item; 1 turno com apresentado=0 |
| CARTAO | **LOW** | Expected net × N turnos vs identified gross — número enganoso |
| PIX | **LOW** | Agregado sem correlação transacional |

### UI validation (Fase 14)

**PENDING** — UI legado não executada neste ambiente; sem alteração de código só para subir frontend. Disclaimer de API presente no DTO.

### Bugs found (não corrigidos nesta task)

| Severity | Bug |
|----------|-----|
| **BLOCKER** | CARTAO EXPECTED usa `sum(cardBreakdown.expectedNet)` (período) em **cada** item de turno; CASH-01 compara isso com identified **gross** → exposição falsa ~−14k enquanto D02 fecha CARTAO com diferença 0. |
| **HIGH** | Label `data_scope=CASH_CLOSING` no CARTÃO da exposição é enganoso quando expected não é CASH_CLOSING gross. |
| **MEDIUM** | `sangria` sempre `None` em `build_items`; regra `apurado−sangria` documentada mas não aplicada por item na ingestão atual. |
| **LOW** | `test_financial_review_inbox` não coleciona neste venv (`asyncpg` ausente). |

**Nenhuma correção financeira implementada.** Proposta (somente documentação): para CASH-01, EXPECTED CARTAO = `valorApurado` (gross), reservando `expectedNet` para CASH-02/adquirente — **requer revisão humana**.

### Remaining uncertainties

- Semântica operacional do turno DINHEIRO com apresentado=0 (digitação vs parcial).
- Casa Caiada (5555) não revalidada neste live (usou VIP 11495).
- UI runtime não exercitada.
- Sangria por item nunca populada no path atual.

### Product Gate (live)

**VALIDATION_FAILED**

Motivo: source trace e reprodução manual confirmam o cálculo, mas **EXPECTED/IDENTIFIED no CARTÃO misturam liquidação líquida estimada com fechamento bruto**, produzindo exposição financeiramente enganosa e insegura para usuário real. Unit tests (13/22 path) **não** substituem esta falha semântica.

### Recommended next action

1. Revisão humana CTO/PO do blocker CARTÃO (não merge CASH-01 como está).  
2. Decisão de regra: EXPECTED CASH-01 = sempre gross `valorApurado` (e sangria só DINHEIRO com fonte correta) **ou** separar produto “exposição fechamento” vs “exposição líquida cartão”.  
3. Só após correção aprovada: re-live + UI + commit.  
4. **Não** iniciar CASH-02 / Expense / Money Hunter / OFX / EDI / FIN-03.

---

## DOMAIN CORRECTION

Validation / correction date: 2026-08-11  
Branch: `feature/cash-01-exposure`  
HEAD base: `33a880ad3bbfbf4a230843ada2fabe1363601185` (alterações ainda uncommitted)  
Worktree: `C:/Users/mlisb/OneDrive/ProjetosAntigravy/LOGOS SPACE/Api_WebPosto_CASH01_CLEAN`  
Empresa live: **74014 — POSTO DOZE FILIAL II**  
Artifacts: `tmp_cash01_domain_validation.json`, `tmp_dump_caixa_0608.py`

### Old assumption (preservado)

CASH-01 V0 usava `expected_realized()` → CARTÃO = `sum(cardBreakdown.expectedNet)` vs identified gross → falso gap (VIP 10/08: −14.388,71).  
Gate anterior: **VALIDATION_FAILED**.

### Evidence from WebPosto

1. **Prestação de Contas (UI report, 06/08/2026 1º Turno)** — valores informados pelo PO:
   - TOTAL Apresentado 52.258,82 / Apurado 52.184,76 / Diferença **+74,06**
   - DINHEIRO 12.204,45 / sangria 12.204,45 / 12.130,39 / **+74,06**
   - CARTÃO 21.476,14 / 21.476,14 / **0** (TEF total igual)
   - Transf. Crédito 13.917,26 / 13.917,26 / **0**

2. **API live CAIXA_APRESENTADO (mesmo dia/empresa, caixa 4399370, 1º TURNO, consolidado=True)**:
   - TOTAL `apurado=52184.76` (bate com Prestação) / `diferenca=-80.94`
   - `dinheiroApresentado=12003.45` `dinheiroApurado=12084.39` `dinheiroDiferenca=-80.94`
   - `cartaoApresentado=cartaoApurado=21504.14` diff 0
   - `transfBancApresentado=transfBancApurado=13937.26` diff 0
   - **Não há campo sangria** no payload CAIXA_APRESENTADO (explica sangria=null no D02 item)

### Correct financial semantics

| Conceito WebPosto | Campo D02 / CASH-01 |
|-------------------|---------------------|
| APRESENTADO | `valorApresentado` ← `*Apresentado` |
| APURADO | `valorApurado` ← `*Apurado` |
| DIFERENÇA | `diferenca` ← `*Diferenca` **ou** apresentado − apurado |
| SANGRIA | coluna UI Prestação; API item = null; meta `sangriaTotal` separado — **não entra na fórmula da diferença** |

Convenção de sinal **confirmada no campo nativo API**: `dinheiroDiferenca = -80.94 = 12003.45 − 12084.39` → **diferença = apresentado − apurado**.

CASH-01 V1 **não** usa `expected_realized` / `expectedNet`.

### Source mapping

```
WEBPOSTO APRESENTADO → ReconciliationItem.valorApresentado → presented_amount
WEBPOSTO APURADO     → ReconciliationItem.valorApurado     → calculated_amount
WEBPOSTO DIFERENÇA   → ReconciliationItem.diferenca        → difference_amount
WEBPOSTO SANGRIA     → (UI Prestação) / meta.sangriaTotal; item.sangria não populado em build_items
D02 APRESENTADO/APURADO/DIFERENÇA → NATURE_FIELD_MAP + CAIXA_APRESENTADO
```

Aliases mantidos (compat): `expected_amount=calculated`, `identified_amount=presented`, `exposure_amount=difference` (**sinal WebPosto**, não o antigo expected−identified).

### Code change

- `cash_exposure_service.py` — reescrito para Apresentado/Apurado/Diferença; breakdown DINHEIRO/CARTAO/TRANSFERENCIA_CREDITO/PRE_PAGO; `closing_status` + `reliable_for_closing_audit`
- UI legado — terminologia “Divergência de Fechamento” / Apresentado / Apurado / Diferença
- Testes — golden conceitual + anti-regressor expectedNet×N turnos
- **Não** alterou `nature_strategies.expected_realized` (ainda usado pelo PreEngine D02; CASH-01 não consome)

### Regression tests

```
tests/unit/test_cash_exposure_service.py + test_cash_reconciliation_service.py
→ 13 passed
```

### Live validation 06/08 (API)

| | Prestação UI (PO) | CASH-01 / API CAIXA_APRESENTADO |
|--|-------------------|--------------------------------|
| TOTAL Apurado | 52.184,76 | **52.184,76** MATCH |
| TOTAL Apresentado | 52.258,82 | 52.103,82 **NO** |
| TOTAL Diferença | +74,06 | **−80,94** NO (sinal e valor) |
| DINHEIRO | 12.204,45 / 12.130,39 / +74,06 | 12.003,45 / 12.084,39 / −80,94 NO |
| CARTAO | 21.476,14 / 0 | 21.504,14 / **0** (semântica OK; valor absoluto ≠ Prestação) |
| TRANSF. CRÉDITO | 13.917,26 / 0 | 13.937,26 / **0** (rótulo correto; ≠ PIX) |

**GOLDEN PRESTAÇÃO MATCH: NO** — apurado total idêntico sugere mesma competência; apresentado/DINHEIRO e sinal divergem (possível drift pós-screenshot, visão de relatório distinta, ou ajuste de sangria só na UI).

### Validation 08–10/08

Planilha `DIA08ATE11AGOSTO_POstoDOzeFilia.xlsx` **não encontrada** no worktree/Downloads/Desktop — validação secundária por planilha **BLOCKED**.

Live API (74014):

| DATE | consolidação API | presented | calculated | difference | CARTAO diff | TRANSF diff | DINHEIRO diff |
|------|------------------|-----------|------------|------------|-------------|-------------|---------------|
| 08/08 | NOT_CONSOLIDATED (OPEN) | 59.649,62 | 63.252,36 | −3.602,74 | 0 | 0 | −3.602,74 |
| 09/08 | NOT_CONSOLIDATED (OPEN) | 56.012,23 | 57.060,35 | −1.048,12 | 0 | 0 | −1.048,12 |
| 10/08 | NOT_CONSOLIDATED (OPEN) | 49.151,91 | 51.158,58 | −2.006,67 | 0 | 0 | −2.006,67 |
| 11/08 | NOT_CONSOLIDATED (ABERTO) | 0,00 | 2.971,28 | −2.971,28 | ≠0 (apresentado 0) | ≠0 | ≠0 |

`reliable_for_closing_audit=false` para 08–11. Apenas 06/08 veio `CONSOLIDATED` / CLOSED.

### Remaining uncertainty

- Por que Prestação UI (PO) ≠ CAIXA_APRESENTADO nos campos de DINHEIRO/apresentado no mesmo dia.
- Origem da coluna Sangria na Prestação (não existe no payload CAIXA_APRESENTADO).
- “Fechado” na planilha vs `consolidado` na API (08–10 OPEN na API).
- UI runtime ainda não exercitada após rename.

### Product challenge (recomendações — não implementadas)

- CASH-01 V1 **replica** o batimento nativo; valor LOGOS futuro = priorização, histórico, responsável, thresholds.
- Threshold sugerido: abs(diff) ≥ R$ 1,00 (ignorar centavos) e/ou ≥ 0,05% do apurado do turno.
- Aberto/não consolidado: nunca tratar como fechamento concluído (`reliable_for_closing_audit`).
- Ainda **não** é Cash Hunter (sem banco/OFX/EDI/recebível/alerta engine).

### Product Gate (domain)

**CASH01_DOMAIN_FAILED** *(superseded by FINAL DOMAIN RECONCILIATION below)*

Motivos (histórico):
1. Golden Prestação 06/08 **não** reproduzido nos valores de Apresentado/DINHEIRO/sinal (apesar do apurado total e da semântica CARTÃO=0 via API).
2. Planilha 08–11 ausente — match tabular não comprovado.
3. Regra CARTÃO/expectedNet **corrigida** e testada; domínio API **coerente** — insuficiente sozinho para gate VALIDATED sob critério do golden Prestação.

---

## FINAL DOMAIN RECONCILIATION

Date: 2026-08-11  
Empresa: **74014 — POSTO DOZE FILIAL II**  
Artifact: `tmp_cash01_final_reconciliation.json`  
Golden planilha: valores fornecidos pelo PO (arquivo xlsx não necessário no worktree)  
Prestação golden: 06/08/2026 1º Turno (valores PO)  
Code financial rule: **unchanged** in this task (investigation only)

### 08/08 golden validation

| Metric | Golden planilha | CASH-01 / API | Match |
|--------|-----------------|---------------|-------|
| Situação planilha | Fechado | `fechado=True`, `consolidado=False` | Fechado≠Consolidado |
| PRESENTED | 59.649,62 | **59.649,62** | YES |
| CALCULATED (apurado) | 63.252,36 | **63.252,36** | YES |
| DIFFERENCE | −3.602,74 | **−3.602,74** | YES |
| Lanes apresentado | Dinheiro/Cartão/Despesa/Vale/Transf | todos | YES |

APURADO MATCH: YES · DIFFERENCE MATCH: YES · PRESENTED RECONSTRUCTED MATCH: YES  
STATUS MATCH (Fechado vs nosso `closing_status=OPEN`): **NO** — ver semântica abaixo (não invalida números).

### 09/08 golden validation

| Metric | Golden | CASH-01 | Match |
|--------|--------|---------|-------|
| PRESENTED | 56.012,23 | 56.012,23 | YES |
| CALCULATED | 57.060,35 | 57.060,35 | YES |
| DIFFERENCE | −1.048,12 | −1.048,12 | YES |
| `fechado` / `consolidado` | Fechado | True / False | Fechado≠Consolidado |

### 10/08 golden validation

| Metric | Golden | CASH-01 | Match |
|--------|--------|---------|-------|
| PRESENTED | 49.151,91 | 49.151,91 | YES |
| CALCULATED | 51.158,58 | 51.158,58 | YES |
| DIFFERENCE | −2.006,67 | −2.006,67 | YES |
| `fechado` / `consolidado` | Fechado | True / False | Fechado≠Consolidado |

### 11/08 (aberto — controle)

- Planilha: Aberto, apresentado≈0, apurado 2.762,42  
- API agora: `fechado=False`, presented=0, calculated=3.449,60 (mutável)  
- **Não** usar como evidência de divergência consolidada. Confirma tratamento de caixa aberto.

### 06/08 — investigação R$155 (field-by-field)

Caixa API: **4399370**, 1º TURNO, `fechado=True`, `consolidado=True`, `fechamento=2026-08-07T00:08:23-03:00`

| NATUREZA | PRESTAÇÃO APRESENTADO | API RAW | D02 | DELTA (Prest−API) |
|----------|----------------------|---------|-----|-------------------|
| DINHEIRO | 12.204,45 | 12.003,45 (`ap_dinheiroApresentado`) | 12.003,45 | **+201,00** |
| NOTAS | 424,42 | 424,42 | 424,42 | 0 |
| CHEQUE_VISTA | — | 0 | 0 | 0 |
| CHEQUE_PRE | — | 0 | 0 | 0 |
| CARTAO | 21.476,14 | 21.504,14 | 21.504,14 | **−28,00** |
| CARTA_FRETE | — | 0 | 0 | 0 |
| VALE_CLIENTE | — | 0 | 0 | 0 |
| DESPESA | 2.647,55 | 2.645,55 | 2.645,55 | **+2,00** |
| EMPRESTIMO | — | 0 | 0 | 0 |
| PRE_PAGO | — | 0 | 0 | 0 |
| VALE_FUNCIONARIO | 1.589,00 | 1.589,00 | 1.589,00 | 0 |
| CHEQUE_PAGAR | — | 0 | 0 | 0 |
| TRANSFERENCIA_CREDITO | 13.917,26 | 13.937,26 | 13.937,26 | **−20,00** |
| TRANSFERENCIA_DEBITO | — | 0 | 0 | 0 |
| FUNDO_CAIXA_DEBITO | — | 0 | 0 | 0 |
| **SUM DELTA** | | | | **+155,00** |

Prova: `201 − 28 + 2 − 20 = 155`.

**Apurado:** totais Prestação = API = **52.184,76**. Deltas de apurado por natureza: DINHEIRO +46, CARTAO −28, DESPESA +2, TRANSF −20 → **SUM = 0** (redistribuição entre naturezas, total estável).

#### R$155 ROOT CAUSE

**Não é um lançamento único de R$155.**  
É a **soma algébrica de drifts por natureza** entre o snapshot da Prestação UI (PO) e o payload atual `CAIXA_APRESENTADO`.

Classificação: **SOURCE_DATA_DRIFT** + **REPORT_TRANSFORMATION** / **TEMPORAL_MUTATION**  
**Não** é `CASH01_BUG`, nem `D02_MAPPING_BUG` (D02 = API raw).  
CASH-01 reproduz fielmente a API; a Prestação diverge no **apresentado** e redistribui **apurado** entre lanes.

Perguntas:

| Pergunta | Achado |
|----------|--------|
| Edição posterior? | POSSIBLE (temporal) |
| Movimento adicional? | POSSIBLE (offsets CARTÃO/TRANSF) |
| Sangria? | NÃO explica o delta (fórmula não usa sangria; meta.sangriaTotal=0) |
| Endpoint incompleto? | UNLIKELY — totais de apurado batem; campos presentes |
| Prestação ≠ CAIXA_APRESENTADO? | **YES — confirmado** |
| Turno/caixa errado? | UNLIKELY — mesmo 1º TURNO, caixa 4399370, apurado total idêntico |
| Lançamento exato 155? | **NÃO** — composição 201−28+2−20 |

### Sangria conclusion

- Prestação: sangria DINHEIRO = 12.204,45 (= apresentado na UI).  
- Item D02: `sangria=null` porque `build_items` passa `sangria=None` e **não há campo sangria** em CAIXA_APRESENTADO.  
- `meta.sangriaTotal` neste dia = **0** (fonte DESPESAS/agregado — não espelha a coluna da Prestação).  
- Diferença WebPosto = apresentado − apurado **sem** subtrair sangria (evidência Prestação 74,06 e API −80,94).  
- **CASH-01 não deve descontar sangria da diferença.** Nenhuma correção de sangria necessária para o domínio V1.

### CARTÃO

- Prestação 06/08: 21.476,14 / 0 — API atual: 21.504,14 / **difference 0**.  
- 08–10: CARTÃO apresentado = apurado → difference 0.  
- expectedNet **não** usado. Teste anti-regressão permanece.  
**CARTAO: VALID**

### TRANSFERENCIA / PRE_PAGO

- Label `TRANSFERENCIA_CREDITO` (não PIX genérico).  
- PRE_PAGO separado (0 no 06/08).  
- PREMMIA PIX no TEF permanece contexto de **cartão/captura**, não natureza TRANSF.  
**TRANSFERENCIA/PRE_PAGO: VALID**

### Fechado vs Consolidado

| Conceito | Campo API | 06/08 | 08–10 | 11/08 |
|----------|-----------|-------|-------|-------|
| **Fechado** | `fechado` (+ `fechamento` timestamp) | True | **True** | False |
| **Consolidado** | `consolidado` / `ap_consolidado` | True | **False** | False |

**WHAT DOES "Fechado" MEAN?** Turno/caixa encerrado operacionalmente (`fechado=true`, há `fechamento`).  
**WHAT DOES "Consolidado" MEAN?** Flag separada de consolidação contábil/administrativa.  
**CAN CLOSED && !CONSOLIDATED?** **YES** — comprovado em 08/09/10 com números estáveis = planilha.

D02 `_consolidation_status` hoje lê só `consolidado*` / texto situacao — **não lê `fechado`**. Por isso CASH-01 reportou `closing_status=OPEN` em 08–10 apesar de `fechado=True`.

### reliable_for_closing_audit — recommendation (NÃO implementado)

Produto: caixa **Fechado** já é analisável como divergência de fechamento, mesmo se **não consolidado**.  
Consolidação é sinal de maturidade/contábil, não pré-requisito para ver Apresentado×Apurado.

Recomendação futura (após aprovação humana):

```
reliable_for_closing_audit ≈ fechado == true
  (e apresentado/apurado presentes)
NÃO exigir consolidado == true
Aberto (fechado=false): exibir com disclaimer, não priorizar como gap consolidado
```

**Nenhuma alteração de código nesta task.**

### Source data risks

- Prestação UI pode divergir de CAIXA_APRESENTADO em apresentado/lanes com apurado total idêntico.  
- Caixa aberto muta apurado (11/08).  
- Sangria da Prestação sem espelho fiel no item D02.

### Code bugs confirmed

| Item | Tipo | Ação nesta task |
|------|------|-----------------|
| expectedNet no fechamento | Corrigido em domain correction anterior | Mantido |
| Status OPEN quando `fechado=True` e `consolidado=False` | **Status mapping gap** (não bug financeiro) | Documentado; sem patch |
| Regra financeira CASH-01 vs planilha 08–10 | Nenhum | — |

### Tests

`test_cash_exposure_service` + `test_cash_reconciliation_service` → **13 passed** (sem alteração de regra).

### Product Gate (final)

**CASH01_DOMAIN_VALIDATED**

Justificativa:
1. 08/09/10 batem **exatamente** com golden da planilha (presented, calculated, difference + lanes).  
2. CARTÃO difference=0; sem expectedNet.  
3. TRANSFERENCIA_CREDITO / PRE_PAGO corretamente rotulados.  
4. Sinal diferença = apresentado − apurado (confirmado).  
5. Fechado vs Consolidado **entendido** com evidência API.  
6. Drift R$155 do 06/08 **explicado** como SOURCE_DATA_DRIFT multi-natureza Prestação↔API — **não invalida** CASH-01 (espelha API; apurado total idêntico).

**Sem commit/PR/merge nesta entrega.**


---

## Closing Status Semantics (CASH-01S)

Date: 2026-08-11  
Commit base CASH-01: `8b9eda6`  
Artifact live: `tmp_cash01s_status_live.json`

### Fechado vs Consolidado

| Conceito | Campo WebPosto | Item D02 | CASH-01 DTO |
|----------|----------------|----------|-------------|
| Fechamento operacional | `fechado` | `caixaFechado` | `closing_status` CLOSED/OPEN/UNKNOWN |
| Consolidação administrativa | `consolidado` | `consolidationStatus` | `is_consolidated` true/false/unknown/mixed |

**Fechado ≠ Consolidado.** Caixa pode estar `fechado=true` e `consolidado=false` (08–10 comprovado) com números estáveis.

### Regra final

`
closing_status = f(fechado)
  True  → CLOSED
  False → OPEN
  ausente → UNKNOWN   # não inventa CLOSED

is_consolidated = f(consolidado)   # atributo separado

reliable_for_closing_audit = (closing_status == CLOSED)
  # responde: o caixa terminou o fechamento e pode ser auditado?
  # NÃO exige consolidação administrativa
`

Valores financeiros (presented/calculated/difference) **não** mudam com CASH-01S.

### Exemplos live 08–11 (74014)

| DATE | closing_status | is_consolidated | reliable | presented | calculated | difference | fin vs golden |
|------|----------------|-----------------|----------|-----------|------------|------------|---------------|
| 08/08 | CLOSED | false | true | 59649.62 | 63252.36 | -3602.74 | YES |
| 09/08 | CLOSED | false | true | 56012.23 | 57060.35 | -1048.12 | YES |
| 10/08 | CLOSED | false | true | 49151.91 | 51158.58 | -2006.67 | YES |
| 11/08 | OPEN | false | false | 0.00 | mutável | — | presented=0 OK |

### Impacto no Cash Hunter

- Priorizar divergências com `reliable_for_closing_audit=true`.
- Caixa OPEN: exibir com disclaimer; não tratar como gap consolidado de fechamento.
- Consolidação futura pode alimentar workflow administrativo separado — não bloqueia CASH-01.

### Product Gate CASH-01S

**CASH01_STATUS_VALIDATED**

---

## Closing Finality Semantics (CASH-01S2)

Date: 2026-08-11  
Corrige `af035ca`: `reliable_for_closing_audit = (closing_status == CLOSED)` era forte demais.  
Artifact: `tmp_cash01s2_finality_live.json`

### Consumers review

| Consumer | Uso anterior de `reliable` | Impacto |
|----------|------------------------------|---------|
| `cash_exposure_service` | derivava do CLOSED | atualizado |
| UI `cashReconciliation.js` | label SIM/NÃO | passou a exibir `audit_state` |
| Outros módulos produção | nenhum | — |

Nenhum consumidor externo assumia `reliable == can inspect` além da UI CASH-01.

### Eixos independentes

| Eixo | Valores |
|------|---------|
| FECHAMENTO | OPEN / CLOSED / UNKNOWN |
| CONSOLIDAÇÃO | false / true / unknown / mixed |
| FINALIDADE (`audit_state`) | NOT_READY / PROVISIONAL / FINAL |

### Matriz

| Caso | fechado | consolidado | closing_status | audit_state | reliable_for_closing_audit |
|------|---------|-------------|----------------|-------------|----------------------------|
| OPEN | false | false | OPEN | NOT_READY | false |
| CLOSED MUTABLE | true | false | CLOSED | PROVISIONAL | false |
| FINAL | true | true | CLOSED | FINAL | true |
| UNKNOWN | ausente | * | UNKNOWN | NOT_READY | false |

**PROVISIONAL permanece visível no CASH-01** (detecção antecipada). Não é excluído.  
**FINAL** = estável para auditoria de fechamento consolidada.  
Nenhum estado implica perda/fraude/dinheiro desaparecido.

### `reliable_for_closing_audit` decision

Mantido no contrato por compatibilidade, com semântica **inequívoca**:

`
reliable_for_closing_audit ≡ (audit_state == FINAL)
`

Não usar como "pode inspecionar". Inspeção antecipada = `audit_state in {PROVISIONAL, FINAL}` ou simplesmente `has_data`.

### Live 08–11 (valores financeiros inalterados)

| DATE | STATUS | AUDIT_STATE | FINANCIAL UNCHANGED |
|------|--------|-------------|---------------------|
| 08/08 | CLOSED | PROVISIONAL | YES (59649.62 / 63252.36 / -3602.74) |
| 09/08 | CLOSED | PROVISIONAL | YES |
| 10/08 | CLOSED | PROVISIONAL | YES |
| 11/08 | OPEN | NOT_READY | presented=0 |

### Source drift / mutabilidade (06/08)

Caixas `CLOSED + NOT_CONSOLIDATED` **podem sofrer alterações** até a consolidação.  
Isso é uma **possível** explicação de domínio para divergências temporais Prestação ↔ CAIXA_APRESENTADO (ex.: delta R no 06/08), mas **não** declara causa definitiva sem evidência adicional.

### Cash Hunter

- PROVISIONAL → "Divergência provisória" (priorizar com menor confiança)
- FINAL → "Divergência consolidada"
- NOT_READY → não tratar como fechamento concluído

### Product Gate CASH-01S2

**CASH01_FINALITY_VALIDATED**
