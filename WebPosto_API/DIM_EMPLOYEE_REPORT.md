# DIM EMPLOYEE — F04.0 · Agente 1

Janela: **7d** · {'inicio': '2026-06-01', 'fim': '2026-06-07'}

| Campo | Status |
|-------|--------|
| employeeId / employeeCode | `funcionarioCodigo` |
| employeeName | `/INTEGRACAO/FUNCIONARIO.nome` |
| employeeCpf | `FUNCIONARIO.cpf` |
| employeeReference | `funcionarioReferencia` |
| employeeStatus | `ativo` → ATIVO/INATIVO |
| empresaCodigo | `FUNCIONARIO.empresaCodigo` |

## Métricas

| Métrica | Valor |
|---------|-------|
| Total cadastro | 84 |
| Ativos | 43 |
| Nominalização | 100.0% |

Serviço: `EmployeeDimensionService` · endpoint registrado: `funcionario`
