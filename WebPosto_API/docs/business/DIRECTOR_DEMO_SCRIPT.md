# LOGOS — Script de Demonstração para Diretoria (5 minutos)

Produto primeiro. Sem arquitetura. Sem tecnologia.

## MINUTO 0–1 — O que o LOGOS encontrou na rede

1. Abrir: **Executivo → Visão da rede**
2. Mostrar **2 decisões reais** (#1 POSTO DOZE, #2 POSTO VIP)
3. Reforçar: ranking automático em **3 postos** — não é um caso isolado
4. Mostrar **Sinais em observação** (recebíveis) — deixar claro que não são decisões

Frase sugerida:

> "O LOGOS analisou os três postos e encontrou duas decisões reais neste período. A primeira é no POSTO DOZE: R$ 7.501 em vales acima do padrão. A segunda, no POSTO VIP: quase R$ 6.000 em NF de fornecedor sem histórico no baseline."

## MINUTO 1–2 — Por que a #1 é a prioridade global

1. Clicar **Entender decisão** na decisão #1 (POSTO DOZE)
2. Mostrar título, categoria e comparação período vs referência
3. Reforçar etiqueta **valor estimado** — não é perda confirmada

Frase sugerida:

> "O sistema ranqueou automaticamente. O DOZE ficou em primeiro por exposição e confiança — não porque alguém escolheu o posto."

## MINUTO 2–3 — A segunda decisão prova cobertura da rede

1. Voltar à Visão da rede
2. Apontar **Decisão #2** — POSTO VIP, NF SOUZA CRUZ
3. Clicar **Entender decisão** e mostrar referência à NF

Frase sugerida:

> "Antes só víamos o DOZE. Agora a VIP também tem uma decisão concreta — compra nova de fornecedor que não aparecia no padrão anterior."

## MINUTO 3–4 — Evidências e acompanhamento

1. Na decisão #1, rolar para **lançamentos / evidências**
2. Voltar à home; mostrar **Em acompanhamento** — Marcio de Lima, **3 de 13**
3. Mostrar **Sinais em observação** (recebíveis vencidos)

Frase sugerida:

> "Decisões com evidência. Recebíveis ainda em observação. E a conferência que você já encaminhou ao Financeiro, com progresso visível."

## MINUTO 4–5 — Como o LOGOS acompanha a execução

1. Clicar **Ver acompanhamento**
2. Mostrar status executivo, valor em revisão, origem da decisão
3. Fechar voltando à Visão da rede

Frase sugerida:

> "A Diretoria vê a rede inteira: duas decisões, sinais monitorados e execução financeira em andamento — num só lugar."

## O que NÃO dizer

- FastAPI, React, snapshots, Pydantic, cache
- "O posto está saudável" quando só não houve decisão
- "Você perdeu R$ X" quando o rótulo é **estimado**
- "Só temos um problema" — são **duas decisões reais**

## URL de demonstração

```text
http://127.0.0.1:8046/app/financial?view=owner-diretoria&dataInicial=2026-06-05&dataFinal=2026-07-04
```

(Reinicie a API após deploy para carregar os 4 detectores e as 2 decisões.)
