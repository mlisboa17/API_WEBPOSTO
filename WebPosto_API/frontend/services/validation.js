import { APP_CONFIG } from "../config.js";

/**
 * Validador opcional para ambiente de desenvolvimento.
 * Verifica a presença de chaves esperadas nos payloads da API simulando verificação de contrato.
 * @param {Array|Object} data - Dados retornados da API
 * @param {string[]} expectedKeys - Lista de chaves esperadas baseadas no OpenAPI/Contrato
 * @param {string} endpoint - Nome do endpoint para logging
 */
export function validateResponse(data, expectedKeys = [], endpoint = "API") {
  if (!APP_CONFIG.debugWebPosto) return;

  const rows = Array.isArray(data) ? data : [data];
  if (!rows.length || !rows[0]) return; // Sem dados para validar

  const sample = rows[0];
  const missingKeys = [];
  const extraKeys = [];

  // Checar campos esperados que faltam
  expectedKeys.forEach((key) => {
    if (!(key in sample)) {
      missingKeys.push(key);
    }
  });

  // Checar campos extras que não estavam mapeados
  Object.keys(sample).forEach((key) => {
    if (!expectedKeys.includes(key)) {
      extraKeys.push(key);
    }
  });

  if (missingKeys.length > 0) {
    console.warn(`[VALIDAÇÃO CONTRATO] ${endpoint}: Faltam campos esperados ->`, missingKeys.join(", "));
  }
  
  if (extraKeys.length > 0) {
    console.log(`[VALIDAÇÃO CONTRATO] ${endpoint}: Campos extras omitidos no contrato ->`, extraKeys.join(", "));
  }

  if (missingKeys.length === 0) {
    console.log(`[VALIDAÇÃO CONTRATO] ${endpoint}: Contrato validado com sucesso.`);
  }
}

// Schemas simplificados baseados nos JSDocs gerados (OpenAPI specs transferidos para o Frontend)
export const SCHEMAS = {
  Empresa: ["empresaCodigo", "cnpj", "razao", "fantasia", "cidade", "estado"],
  VendaItem: ["empresaCodigo", "vendaCodigo", "vendaItemCodigo", "dataMovimento", "produtoCodigo", "quantidade", "precoCusto", "totalCusto", "precoVenda", "totalVenda"],
  VendaFormaPagamento: ["empresaCodigo", "vendaCodigo", "dataMovimento", "valorPagamento", "formaPagamentoCodigo"],
  Conta: ["empresaCodigo", "contaCodigo", "descricao", "saldoAtual", "ativo"],
};
