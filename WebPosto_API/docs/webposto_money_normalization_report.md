# Relatorio Tecnico - Normalizacao de Valores Monetarios WebPostos

## Objetivo
Corrigir inflacao/duplicidade de valores monetarios no backend, centralizando a normalizacao de moeda e eliminando duplicidades no fluxo de despesas de rede.

## Investigacao executada
1. Foram inspecionados os endpoints WebPosto e os pontos de conversao monetaria no backend.
2. Em `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE`, os registros-alvo ja chegam com valor decimal correto (ex.: `1648.29`, `1130.0`, `2000.0`, `720.0`, `600.0`).
3. O sintoma de inflacao observado em despesas estava associado a repeticao de linhas no processamento multiempresa de endpoint de rede.

## Padrao confirmado por endpoint
- `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE`: decimal valido (nao aplicar divisao cega por 100).
- Conversoes genericas de string numerica inteira continuam suportando centavos para casos de integracao que enviem inteiro sem separador.

## Correcoes implementadas
1. Criado normalizador central em `src/services/money_normalizer.py` com:
   - `parse_decimal_br`
   - `normalize_cents`
   - `normalize_webposto_money`
   - `normalize_webposto_expense_value`
   - `normalize_webposto_sale_value`
   - `normalize_webposto_account_value`
2. Integracao do normalizador nos pontos principais:
   - `src/services/network_financial_overview_service.py`
   - `src/services/analytics_service.py`
   - `src/application/usecases/fetch_expenses.py`
3. Inserida deduplicacao por chave de negocio em despesas/contas para impedir soma duplicada de registros repetidos.
4. Inseridos logs temporarios de diagnostico de moeda, controlados por `WEBPOSTO_MONEY_DEBUG` (`settings.webposto_money_debug`) para as descricoes-alvo:
   - `ref ao abastecimento do caminhao`
   - `SR. MOISES / COM PEDRO`
   - `salario josinaldo`

## Campos de debug emitidos
- `descricao`
- `valor_bruto`
- `tipo_bruto`
- `valor_convertido_atual`
- `valor_normalizado_novo`
- `endpoint_origem`

## Resultado esperado apos correcao
Para os registros-alvo, os totais ficam preservados sem inflacao por conversao indevida e sem duplicidade:
- `R$ 1.648,29`
- `R$ 3.130,00`
- `R$ 1.320,00`
