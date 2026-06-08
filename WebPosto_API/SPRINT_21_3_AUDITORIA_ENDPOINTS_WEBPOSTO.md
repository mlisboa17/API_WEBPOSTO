# SPRINT 21.3 - AUDITORIA DE ENDPOINTS WEBPOSTO

Status: ABERTA

## Objetivo
- identificar todos os endpoints 404
- identificar endpoints obsoletos
- identificar substitutos oficiais na documentacao WebPosto
- remover dependencias quebradas do Dashboard Executivo
- garantir estabilidade do ambiente analitico

## Backlog inicial
- [ ] Levantar todos os endpoints chamados por frontend/services/api.js e src/gateway/webposto_client.py
- [ ] Executar varredura de status HTTP por endpoint (janela curta e janela semanal)
- [ ] Separar 404 por categoria: rota inexistente, credencial, parametros, endpoint legado
- [ ] Mapear substitutos oficiais na documentacao WebPosto
- [ ] Atualizar camada de servicos para fallback oficial
- [ ] Remover chamadas quebradas do Dashboard Executivo
- [ ] Validar novamente Sprint 21.2 apos estabilizacao dos endpoints
