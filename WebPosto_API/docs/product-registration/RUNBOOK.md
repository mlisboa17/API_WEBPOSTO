# Runbook — cadastro de produtos

## Preflight

Informe `--empresa`. Sem `--execute` o comando só analisa.

Bloqueios comuns: GTIN inválido/inventado/truncado, EAN no checkpoint, SAME_PRODUCT, preço ≤ 0, NCM ausente, custo zero sem `--allow-pending-dfe-cost`, risco fiscal sem `--accept-fiscal-risk`.

## Cadastro individual

`register-one` é dry-run por padrão. `--execute` é recusado na CLI permanente até um operador autorizar um lote novo pelo executor de onda. O executor de onda também escreve só pela fachada `ProductRegistrationService`; não há POST direto ao gateway.

## Lote

`register-batch` consulta o lock. Lote COMPLETED/PARTIAL está LOCKED. SKIPPED_PRE_POST não interrompe. Falha após POST pode interromper.

## Recuperação

1. Não reenviar o mesmo body.
2. Consultar EAN por GET.
3. Se encontrado e correto: gravar checkpoint e seguir.
4. Se ausente: `RESULT_UNKNOWN` e parar.
5. Se divergente: parar.

## Reexecução

Ondas 1-5 estão encerradas. Não reabrir locks COMPLETED. Novo trabalho usa novo `batch_id`.

## Erros

| Código CLI | Significado |
| --- | --- |
| 0 | sucesso / dry-run aprovado |
| 1 | preflight bloqueado |
| 2 | autorização ausente |
| 3 | empresa diverge do profile |
| 4 | lock impede |
| 5 | escrita recusada (falta autorização de execute) |

HTTP 401/403, RET de rejeição, empresa ≠ 118508 no GET e sentinel indisponível param o lote.
