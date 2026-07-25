# Inteligência Executiva Proativa — adaptação ao WebPosto

## Parecer

A visão do Conselheiro Executivo Digital está alinhada ao LOGOS e reforça princípios
já existentes: decisão antes de gráfico, evidência obrigatória e valor financeiro
mensurável. A implementação, porém, deve respeitar o escopo real das três empresas e
dos departamentos Combustíveis, Conveniência e Lubrificantes.

Clientes, contratos, churn e projetos estratégicos ainda não possuem fontes
homologadas no projeto. Esses domínios ficam explicitamente bloqueados até que
contratos de dados, cobertura e linhagem sejam entregues.

## Regras adotadas

- Proatividade não autoriza execução automática de decisões.
- Nenhum impacto financeiro será inventado; valor ausente será `NOT_QUANTIFIED`.
- Toda recomendação terá regra, período, empresa, departamento e evidência.
- Cobertura incompleta produz bloqueio, nunca lucro ou oportunidade fictícia.
- Revisão humana permanece obrigatória.

## Priorização

| Critério | Peso |
|---|---:|
| Impacto financeiro | 35% |
| Impacto estratégico | 25% |
| Economia de tempo executivo | 20% |
| Redução de risco | 15% |
| Facilidade de implementação | 5% |

Complexidade foi convertida em **facilidade de implementação**, para que pontuação
maior sempre represente uma iniciativa melhor.

## Primeira entrega

O Radar Executivo Diário é gerado após a rotina configurável das 06:00, usando os
lançamentos do dia anterior. Ele registra mudanças de cobertura nas últimas 24 horas,
prioriza até cinco riscos, aponta responsáveis e responde às perguntas executivas
somente quando os dados equivalentes existem.

O radar pode ser consultado em
`GET /api/v1/departmental-governance/proactive-radar`.

## Notificações e valor

Cada prioridade gera notificações idempotentes para Diretoria e, quando crítica ou
uma oportunidade, também para Presidência. A caixa de saída interna é obrigatória;
um webhook HTTPS pode ser configurado para entrega ativa fora do painel.

O ciclo de valor possui quatro estados: `GENERATED`, `ACCEPTED`, `EXECUTED` e
`CONFIRMED`. A estimativa original permanece como potencial. Somente a confirmação
com evidência pode registrar receita gerada, custo evitado, risco mitigado ou horas
executivas economizadas.

O Executive Value Score usa apenas resultados confirmados:

| Componente | Peso |
|---|---:|
| Impacto financeiro | 30% |
| Redução de risco | 25% |
| Eficiência operacional | 15% |
| Velocidade de decisão | 15% |
| Adoção das recomendações | 15% |

## Evolução dos agentes

A separação futura será feita por domínio homologado: Financeiro, Operacional,
Comercial, Governança e Presidência. Um coordenador executivo poderá consolidar as
saídas, mas não poderá remover bloqueios de cobertura nem elevar confiança sem nova
evidência.

Essa separação foi materializada na Sprint 40. Cada parecer especializado mantém a
evidência original, acrescenta justificativa explícita e informa insuficiência de
evidência quando não pode recomendar. O Agente da Presidência registra quais agentes
contribuíram para cada prioridade e não executa ações automaticamente.

## Aprendizado baseado em valor real

O ciclo completo passa por `GENERATED`, `DELIVERED`, `VIEWED`, `ACCEPTED` ou
`REJECTED`, `IMPLEMENTED` e `VALIDATED`. Resultado não validado não alimenta
aprendizado, EVS nem valor gerado.

Cada agente possui métricas próprias de geração, aceitação, implementação, validação,
falsos positivos e valor atribuído. Quando uma recomendação possui mais de um agente,
o valor é dividido entre os participantes para impedir dupla contagem.

O Agent Reliability Score considera precisão histórica, aceitação, implementação e
resultado validado. Sem resultado validado ou falso positivo observado, o score fica
indisponível como `INSUFFICIENT_VALIDATED_OUTCOMES`; nunca recebe nota inicial
inventada.
