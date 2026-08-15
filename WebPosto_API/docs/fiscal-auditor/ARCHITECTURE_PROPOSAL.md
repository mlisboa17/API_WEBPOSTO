# Proposta — auditor fiscal

Camada futura de análise. Não implementada nesta consolidação. Não substitui obrigação legal nem responsabilidade profissional prevista em lei.

## Princípios

- Motor determinístico primeiro. IA só explica e sugere.
- Legislação e tabelas com versão e vigência.
- Evidências rastreáveis. Nenhuma alucinação vira regra.
- Recomendação estruturada: confiança, impacto, fonte, vigência, contestação.
- Toda decisão é auditável.
- Escrita separada da análise. Correção exige aprovação explícita.
- Dados fiscais protegidos; contexto enviado a modelo é sanitizado.

## Fluxo

```
cadastro / DF-e / tabelas
        → regras determinísticas
        → achados
        → (opcional) AiFiscalAdvisorPort
        → recomendação
        → aprovação humana
        → escrita em outro módulo
```

## Contratos

`FiscalAuditInput`, `FiscalAuditFinding`, `FiscalAuditEvidence`, `FiscalAuditRule`, `FiscalAuditRecommendation`, `AiFiscalAdvisorPort`.

A porta de IA recebe só contexto sanitizado, devolve recomendação, não executa escrita e não altera regras determinísticas.
