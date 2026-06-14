# IA-4 — Endpoint Wrappers

## Wrappers padronizados

| Método | Endpoint |
|--------|----------|
| `get_venda` | `/INTEGRACAO/VENDA` |
| `get_venda_item` | `/INTEGRACAO/VENDA_ITEM` |
| `get_nfce` | `/INTEGRACAO/NFCE` |
| `get_abastecimento` | `/INTEGRACAO/ABASTECIMENTO` |
| `get_lmc_rede` | `/INTEGRACAO/CONSULTAR_LMC_REDE` |
| `get_produto` | `/INTEGRACAO/PRODUTO` |
| `get_produto_empresa` | `/INTEGRACAO/PRODUTO_EMPRESA` |
| `get_conta` | `/INTEGRACAO/CONTA` |
| `get_plano_conta_gerencial` | `/INTEGRACAO/PLANO_CONTA_GERENCIAL` |

## Parâmetros comuns

Todos aceitam:

```text
empresa_codigo
data_inicial
data_final
extra_params
timeout_s (via request)
```

Injeção automática via `build_params()`.
