# Backup e restauração dos dossiês de auditoria

## Política

- Retenção padrão: 2.555 dias (sete anos), nunca inferior a 365 dias.
- Exclusão automática permanece desabilitada.
- Em produção, `PERIODIC_AUDIT_DOSSIER_BACKUP_DIR` deve apontar para volume privado,
  criptografado e separado do armazenamento primário.
- PDF e manifesto são copiados juntos e validados por SHA-256.
- Toda criação, reutilização ou restauração registra autor e horário.

## Operação

1. Gerar o backup com `POST /api/v1/auditorias-periodicas/execucoes/{id}/dossie-backup`.
2. Conferir com `GET /api/v1/auditorias-periodicas/execucoes/{id}/dossie-backup-integridade`.
3. Restaurar somente quando o arquivo primário não existir, usando
   `POST /api/v1/auditorias-periodicas/execucoes/{id}/dossie-restaurar`.
4. Confirmar que o SHA-256 restaurado é igual ao manifesto original.

A restauração não sobrescreve arquivo primário íntegro, divergente ou corrompido.
Backup adulterado, incompleto ou sem manifesto é bloqueado.
