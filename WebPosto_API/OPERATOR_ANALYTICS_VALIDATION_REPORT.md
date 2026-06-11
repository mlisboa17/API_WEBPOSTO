# OPERATOR ANALYTICS VALIDATION — P0 · IA-3

| Cenário | Resultado |
|---------|-----------|
| cashRiskScore=None | PASS — sort sem exception |
| cashRiskScore="" | PASS — trata como 0.0 |
| cashRiskScore ausente | PASS — trata como 0.0 |
| fechamentos=None | PASS — safe_int |
| dados completos | PASS — rankings preservados |
