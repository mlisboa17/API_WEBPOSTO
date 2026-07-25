# Teste funcional autenticado

Data: 24/07/2026

## Resultado

- Login inválido rejeitado com HTTP 401.
- Login válido aceito com perfil `director`.
- Renovação da sessão aceita com HTTP 200.
- Logout concluído com HTTP 200.
- Mutação sem autenticação rejeitada antes e depois do logout.
- Nenhuma mutação autenticada foi persistida durante o teste.

## Interface departamental

- As seis abas trocaram corretamente:
  Presidência, Financeiro, Comercial, Operacional, Alertas e saúde e Auditorias.
- A seleção da empresa `5555` foi aplicada.
- O intervalo de 17/07/2026 a 23/07/2026 foi aplicado.
- O conteúdo foi recarregado sem erro de console.
- Foram encontrados seis ciclos de auditoria e nove alertas, sem alertas críticos.

## Interface executiva

- O painel do Presidente carregou com as três empresas licenciadas.
- O seletor de período abriu e reconheceu o intervalo de sete dias.
- O painel continuou operável sem erros de console.

## Achados

1. O `.env` possui uma chave inválida próxima da linha 94: o nome contém
   espaços. O valor não foi lido nem registrado nesta evidência.
2. A interface principal ainda não oferece uma tela de login; a autenticação é
   exercida diretamente pela API.
3. A DRE do painel permanece bloqueada aguardando homologação, que é o estado
   funcional apresentado pelo sistema e não um erro de renderização.

## Automação adicionada

Foram adicionados testes de regressão para:

- renovação sem cookie;
- ciclo completo de login, renovação e logout;
- invalidação da renovação após logout.

