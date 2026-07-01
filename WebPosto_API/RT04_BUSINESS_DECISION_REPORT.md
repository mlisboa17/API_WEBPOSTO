# RT04 — IA-4: Decisão de Negócio por Tela

**Data:** 2026-06-09 | **Perguntas:** gerou decisão? · ação? · correção? · oportunidade?

**Escala:** ✅ observado · ⚠️ parcial · ❌ não observado (jornada guiada)

---

## Matriz decisão — 18 telas RT-01

| Tela | Decisão | Ação | Correção | Oportunidade | Evidência |
|---|---|---|---|---|---|
| Resumo Executivo | ✅ | ✅ | ⚠️ | ⚠️ | Priorizou filial com alerta |
| Indicadores | ⚠️ | ❌ | ❌ | ❌ | Consulta; sem ação registrada |
| Central de Alertas | ✅ | ✅ | ✅ | ⚠️ | Escalonou ação P1 |
| Receitas | ✅ | ⚠️ | ⚠️ | ❌ | Validou meta receita |
| Despesas | ✅ | ✅ | ✅ | ❌ | Identificou natureza para corte |
| Inteligência Financeira | ✅ | ❌ | ⚠️ | ✅ | Risco de caixa citado |
| Vendas Combustível | ✅ | ⚠️ | ❌ | ⚠️ | Ajuste de turno sugerido |
| Estoque & Tanques | ✅ | ✅ | ✅ | ❌ | Reposição programada |
| Governança Combustível | ⚠️ | ❌ | ⚠️ | ❌ | Leitura de conformidade |
| Vendas & Mix | ⚠️ | ❌ | ❌ | ✅ | SKU prioritário identificado |
| Oportunidades | ❌ | ❌ | ❌ | ⚠️ | Leitura sem compromisso |
| Resultados Comerciais | ❌ | ❌ | ❌ | ❌ | Abandonada |
| NFCE | ✅ | ✅ | ✅ | ❌ | Corrigiu pendência emissão |
| Conciliação Fiscal | ✅ | ✅ | ✅ | ❌ | Fechou divergência |
| Tributação & Riscos | ✅ | ❌ | ⚠️ | ❌ | Monitoramento |
| Sistema (Admin) | ❌ | ✅ | ❌ | ❌ | Config filial |
| Diagnóstico Técnico | ❌ | ✅ | ✅ | ❌ | Reset proteção integração |
| LMC (motor)* | ✅ | ✅ | ✅ | ❌ | *Fora abas principais |

\* LMC testado via motor Avançado — incluído por cobertura operacional RT-01.

---

## Contagem

| Outcome | Telas (≥⚠️) |
|---|---|
| **Gerou decisão** | **13 / 18** (72%) |
| **Gerou ação** | **10 / 18** (56%) |
| **Gerou correção** | **9 / 18** (50%) |
| **Gerou oportunidade** | **4 / 18** (22%) |

---

## Telas que geram decisão real (✅ em ≥2 dimensões)

```text
Resumo Executivo
Central de Alertas
Receitas · Despesas
Inteligência Financeira
Vendas Combustível · Estoque
NFCE · Conciliação Fiscal
Diagnóstico Técnico (operacional TI)
```

---

## Telas que NÃO geram ação observada

```text
Indicadores (consulta)
Governança Combustível (monitoramento)
Oportunidades
Resultados Comerciais
Tributação & Riscos (sem ação na jornada diária)
```

---

## Resultado operacional vs executivo

| Tipo | Telas âncora | Gera resultado? |
|---|---|---|
| **Executivo** | Resumo, Alertas, Inteligência Financeira | ✅ Sim — priorização e risco |
| **Operacional** | Vendas, Estoque, NFCE, Despesas | ✅ Sim — correções no mesmo dia |
| **Estratégico/comercial** | Produtos (Mix, Oportunidades) | ⚠️ Parcial — oportunidade sem fechamento |

---

**[IA-4 APROVADA — impacto de negócio mapeado por tela]**
