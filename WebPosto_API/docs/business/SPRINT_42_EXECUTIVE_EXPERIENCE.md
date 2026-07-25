# Sprint 42 — Executive Experience e Adoção

## Decisão de produto

A entrada padrão da aplicação passa a ser a Presidência 2.0, com quatro blocos:

1. O que exige atenção hoje.
2. O que gera mais valor.
3. Valor gerado pela IA.
4. Perguntas da Presidência.

As análises financeiras e operacionais completas continuam acessíveis por um único
botão, mas não competem com a leitura executiva inicial.

## Padrão visual

- Componentes shadcn/ui já configurados no projeto.
- Recharts para comparar valor comprovado e estimado.
- Tema claro e escuro.
- Tipografia maior, áreas de toque de pelo menos 44px e contraste por tokens.
- Layout de duas colunas em notebook e uma coluna em tablets/telas estreitas.
- Ausência de evidência permanece explícita; nenhum vazio vira oportunidade.

## Métricas de adoção

São coletados apenas: identificador anônimo da sessão, funcionalidade, tipo do evento,
tempo até encontrar informação e número de cliques. Valores financeiros, evidências,
perguntas e conteúdo executivo não entram na telemetria.

Indicadores:

- tempo médio até encontrar uma informação;
- cliques médios;
- funcionalidades utilizadas;
- funcionalidades ignoradas;
- sessões executivas.
