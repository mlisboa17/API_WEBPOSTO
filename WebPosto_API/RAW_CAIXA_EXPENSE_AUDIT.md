# RAW CAIXA EXPENSE AUDIT — P0.1-B

**Empresa:** AP CASA CAIADA (`empresaCodigo=5555`)  
**Data:** 2026-06-08  
**Evidência:** `scripts/p0_1b_caixa_dedup_audit.json` + API WebPosto real

---

## Fechamento operacional identificado

| Campo | Valor |
|-------|------:|
| empresaCodigo | 5555 |
| dataMovimento | 2026-06-08 |
| caixaCodigo | **4343023** |
| turnoCodigo | 1 |
| turno | 1º TURNO |
| pdvCodigo | 15880 |
| funcionarioCodigo | 158924 |
| despesaApurado | 135,00 |
| despesaApresentado | 135,00 |
| despesaDiferenca | 0,00 |

---

## Antes da correção (tela)

| Origem | Qtd | Valor |
|--------|----:|------:|
| financeiro | 2 | R$ 1.912,00 |
| caixa | **2** | **R$ 270,00** |
| pdv | 1 | R$ 135,00 |
| **Total** | **5** | **R$ 2.317,00** |

Linhas duplicadas para o **mesmo** `caixaCodigo=4343023`:

1. `origem=caixa` · R$ 135 · descrição BOBINA TERMICA (match financeiro)
2. `origem=pdv` · R$ 135 · mesmo fechamento
3. `origem=caixa` · R$ 135 · descrição genérica turno/PDV

**Evidência:** R$ 270,00 = R$ 135,00 + R$ 135,00 (mesmo fechamento contado duas vezes como caixa).

---

## Depois da correção

| Origem | Qtd | Valor |
|--------|----:|------:|
| financeiro | 2 | R$ 1.912,00 |
| caixa | **1** | **R$ 135,00** |
| **Total** | **3** | **R$ 2.047,00** |

Campos preservados na linha caixa:

```text
despesaApurado=135.00
despesaApresentado=135.00
despesaDiferenca=0.00
matchFinanceiro=true (BOBINA TERMICA)
```

---

## Fontes brutas

| Endpoint | Papel |
|----------|-------|
| `CAIXA_REDE` | Fechamento turno (metadados PDV/operador) |
| `CAIXA_APRESENTADO` | Valores apurado/apresentado/diferença |
| `CAIXA_APRESENTADO_REDE` | Vazio no dia (0 registros) |
| `CAIXA` | Fallback deduplicado vs REDE |

Merge: `(empresaCodigo, caixaCodigo)` → join caixa + apresentado.
