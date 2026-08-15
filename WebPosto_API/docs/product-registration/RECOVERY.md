# Recuperação

## Desligamento

Se o lock está `RUNNING`, retomar o mesmo `batch_id`. EANs já no checkpoint não reenviam. Não criar lote novo para os mesmos produtos.

## Timeout

Não reenviar. GET por EAN a partir do maior `produtoCodigo` conhecido. Encontrado e íntegro: checkpoint e segue. Ausente: `RESULT_UNKNOWN` e para. Divergente: para.

## Resposta incerta

RET inesperado, sem `codProduto` ou corpo ilegível: parar. Não completar o lote.

## Checkpoint

Gravação atômica. Falha de persistência interrompe a onda. Formato antigo (`execution_id` + `checkpoint_index`) é lido sem reescrita.

## Lock

| status | reexecution | Ação |
| --- | --- | --- |
| RUNNING | OPEN | resume |
| COMPLETED | LOCKED | não reexecutar |
| PARTIAL | LOCKED | não reexecutar; novo batch se houver autorização nova |
| ausente | — | só criar se houver POST previsto |
