# LOGOS — Script de Demonstração para Diretoria (5 minutos)

Produto primeiro. Sem arquitetura. Sem tecnologia.

## MINUTO 0–1 — O que o LOGOS encontrou na rede

1. Abrir: **Executivo → Visão da rede**
2. Mostrar os **3 postos analisados**
3. Destacar **Atenção prioritária** (posto, valor estimado, confiança)
4. Mostrar **Sinais em observação** (se existirem) — deixar claro que não são decisões

Frase sugerida:

> "O LOGOS analisou os três postos da rede neste período. A prioridade agora está no POSTO DOZE: valor estimado acima do comportamento de referência, com confiança alta."

## MINUTO 1–2 — Por que essa é a prioridade

1. Clicar **Entender decisão**
2. Mostrar título, categoria e comparação período vs referência
3. Reforçar etiqueta **valor estimado** — não é perda confirmada

Frase sugerida:

> "Não é um alarme genérico. O LOGOS comparou o período atual com o de referência e isolou o desvio que mais merece sua atenção."

## MINUTO 2–3 — Quais evidências sustentam a decisão

1. Na tela de decisão, rolar para **lançamentos / evidências**
2. Mostrar quantidade e exemplos reais (data, valor, origem)
3. Se houver causa provável, apontar em uma linha

Frase sugerida:

> "Aqui estão os fatos que sustentam a decisão — não é opinião do sistema, são lançamentos reais do WebPosto."

## MINUTO 3–4 — O que a Diretoria fez

1. Voltar à **Visão da rede**
2. Na seção **Em acompanhamento**, mostrar conferência solicitada
3. Mostrar responsável (**Marcio de Lima**) e progresso (**3 de 13**)

Frase sugerida:

> "Você já encaminhou esta conferência para o Financeiro. O responsável assumiu e o LOGOS mostra o andamento item a item."

## MINUTO 4–5 — Como o LOGOS acompanha a execução

1. Clicar **Ver acompanhamento**
2. Mostrar status executivo, valor em revisão, origem da decisão
3. Fechar voltando à Visão da rede

Frase sugerida:

> "A Diretoria decide e acompanha. O Financeiro executa. O LOGOS mantém a rede visível em um só lugar."

## O que NÃO dizer

- FastAPI, React, snapshots, Pydantic, cache
- "O posto está saudável" quando só não houve decisão
- "Você perdeu R$ X" quando o rótulo é **estimado**

## URL de demonstração

```text
http://127.0.0.1:8040/app/financial?view=owner-diretoria&dataInicial=2026-06-05&dataFinal=2026-07-04
```

(Reinicie a API após deploy para expor progresso FIN-03 na home.)
