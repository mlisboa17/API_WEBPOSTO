# Runbook: rotina departamental diária

**Responsável:** Operação de Dados | **Frequência:** diária às 06:00 (`America/Sao_Paulo`)  
**Última atualização:** 2026-07-24 | **Última execução validada:** 2026-07-24

## Objetivo

Materializar, verificar e disponibilizar os fatos das três empresas licenciadas sem
misturar departamentos ou publicar conclusões sobre dados incompletos.

## Janela de processamento

- Por padrão, a rotina inicia todos os dias às **06:00**, no fuso
  `America/Sao_Paulo`.
- Por padrão, a data de referência é o **dia civil anterior** à execução.
- Usuários autorizados podem alterar ativação, horário, fuso e defasagem diária,
  além do dia, horário e tamanho da janela semanal, pela configuração governada.
- Exemplo: a execução de 25/07/2026 às 06:00 processa exclusivamente 24/07/2026.
- Lançamentos do dia corrente não entram nessa execução, mesmo que já estejam
  disponíveis no WebPosto.
- Em reprocessamento manual, a data deve ser informada explicitamente; a rotina não
  amplia o período automaticamente.

## Pré-requisitos

- [ ] API iniciada com as três credenciais no ambiente local seguro.
- [ ] Acesso autorizado ao WebPosto.
- [ ] Diretório privado `.runtime/departmental_facts` disponível.
- [ ] Sessão autenticada com perfil Operação, Diretoria ou Administração.

## Procedimento

Antes de executar os comandos, substituir `AAAA-MM-DD` pela data do dia anterior no
fuso `America/Sao_Paulo`.

### 1. Materializar cada empresa

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8040/api/v1/departmental-facts/materialize?empresaCodigo=11495&data=AAAA-MM-DD"
Invoke-RestMethod -Method Post "http://127.0.0.1:8040/api/v1/departmental-facts/materialize?empresaCodigo=5555&data=AAAA-MM-DD"
Invoke-RestMethod -Method Post "http://127.0.0.1:8040/api/v1/departmental-facts/materialize?empresaCodigo=74014&data=AAAA-MM-DD"
```

**Resultado esperado:** `materialized=true` para todas.  
**Se falhar:** não repetir indefinidamente; registrar empresa, endpoint e erro.

### 2. Verificar saúde

```powershell
Invoke-RestMethod "http://127.0.0.1:8040/api/v1/departmental-governance/health?data=AAAA-MM-DD"
```

**Resultado esperado:** as três empresas com `referenceDayAvailable=true`.  
**Se falhar:** manter o dia indisponível no cockpit e investigar paginação/credencial.

### 3. Avaliar alertas

A avaliação é uma operação autenticada e persistente. Consultas GET nunca
recalculam nem alteram alertas.

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8040/api/v1/departmental-governance/alerts/evaluate?data=AAAA-MM-DD"
```

### 4. Consultar o relatório

```powershell
Invoke-RestMethod "http://127.0.0.1:8040/api/v1/departmental-governance/daily-report?data=AAAA-MM-DD"
```

**Resultado esperado:** alertas com regra, evidência, responsável e prazo.

## Verificação

- [ ] Nenhuma empresa fora de 11495, 5555 e 74014.
- [ ] COMODATO, DIVERSOS e USO E CONSUMO permanecem em quarentena.
- [ ] Diferença de reconciliação igual a zero.
- [ ] Nenhum lucro exibido com despesas incompletas.
- [ ] Segredos ausentes das respostas e logs.

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `MATERIALIZATION_MISSING` | coleta não executada ou falhou | executar uma vez e inspecionar qualidade |
| paginação incompleta | endpoint parou ou mudou contrato | bloquear publicação e revisar evidência |
| despesas incompletas | sem departamento aprovado | manter lucro bloqueado; não ratear |
| conflito de identidade | registros distintos com mesma chave | preservar lote e investigar origem |

## Recuperação

Não apagar o lote anterior. Restaurar somente uma cópia validada para
`.runtime/departmental_facts`, executar a rota de qualidade e comparar totais antes
de liberar o cockpit.

## Escalonamento

| Situação | Responsável |
|---|---|
| falha de API/credencial | Operação de Dados |
| divergência financeira | Diretoria Financeira |
| classificação de grupo/despesa | Gestor do departamento + Financeiro |
| possível deficiência de controle | Auditoria/contador qualificado |
