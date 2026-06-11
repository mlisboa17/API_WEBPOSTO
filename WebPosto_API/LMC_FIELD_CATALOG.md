# LMC — FIELD CATALOG — Sprint D00

## Endpoint produção

| Endpoint | HTTP | Registros | Filiais |
|----------|------|-----------|---------|
| `CONSULTAR_LMC_REDE` | 200 | 28 | 5555, 11495 |

## Campos LMC

| Campo | No payload LMC_REDE |
|---|---|
| empresaCodigo | Sim |
| lmcCodigo | Sim |
| produtoCodigo | Sim |
| produtoLmcCodigo | Sim |
| dataMovimento | Sim |
| abertura | Sim |
| entrada | Sim |
| saida | Sim |
| perdaSobra | Sim |
| escritural | Sim |
| fechamento | Sim |
| disponivel | Sim |
| saldo | Sim |
| precoCusto | Sim |
| ultimoUsuarioAlteracao | Sim |
| lmcTanque | Sim |
| lmcBico | Sim |
| lmcNota | Sim |
| codigo | Sim |

## Extensões bloqueadas (401)

| Endpoint | Status |
|---|---|
| CONSULTAR_LMC_REDE_BICO | 401 — token |
| CONSULTAR_LMC_REDE_TANQUE | 401 — token |
| PRODUTO_LMC | 401 — token |
| BOMBA_REDE | 401 — token |
| BICO_REDE | 401 — token |

## Linhagem proposta (não validada)

```
VENDA_ITEM (litros comercial)
    ↓
ABASTECIMENTO (bico, encerrante, frentista)
    ↓
CAIXA / Prestação (diferença turno)
    ↓
LMC (saida, perdaSobra, lmcBico, lmcTanque)
```

## Uso Logos hoje

- `fuel_analytics_service` — litros físicos via `saida` / `perdaSobra`
- **Não conectado** a caixa, prestação ou accountability
- Reconciliação LMC vs Vendas: **NAO VALIDADA** (baseline combustíveis 1.0)
