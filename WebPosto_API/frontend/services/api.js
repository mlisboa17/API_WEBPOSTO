const API_BASE = "";
import { APP_CONFIG } from "../config.js";
import {
  auditAccounts,
  auditCompanies,
  auditDataQuality,
  auditDre,
  auditExpenses,
  auditKpis,
  auditNetworkCoverage,
  auditOverview,
  auditSales,
  auditStock,
  auditFuelSummary,
} from "./auditSnapshot.js";

const ENABLE_AUDIT_MODE = false;

const WEBPOSTO_ENDPOINT_CONFIG = {
  "/INTEGRACAO/EMPRESAS": { route: "/v1/financial/companies", dataKey: "data" },
  "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE": { route: "/v1/financial/expenses", dataKey: "data" },
  "/INTEGRACAO/VENDA": { route: "/v1/sales", dataKey: "data" },
  "/INTEGRACAO/VENDA_ITEM": { route: "/v1/sales", dataKey: "venda_item" },
  "/INTEGRACAO/VENDA_FORMA_PAGAMENTO": { route: "/v1/sales", dataKey: "venda_forma_pagamento" },
  "/INTEGRACAO/CONTA": { route: "/v1/financial/accounts-payable", dataKey: "data" },
  "/INTEGRACAO/PRODUTO_ESTOQUE": { route: "/v1/stock", dataKey: "data" },
  "/INTEGRACAO/PRODUTO_EMPRESA": { route: "/v1/stock", dataKey: "data" },
};

function toQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    query.set(key, String(value));
  });
  return query.toString();
}

import { apiClient } from './apiClient.js';
import { validateResponse, SCHEMAS } from './validation.js';

async function get(path, params = {}) {
  if (ENABLE_AUDIT_MODE) {
    const page = Number(params.page || 1);
    const limit = Number(params.limit || 50);

    if (path === "/v1/financial/overview") return await auditOverview(params);
    if (path === "/v1/financial/expenses") return await auditExpenses(params, page, limit);
    if (path === "/v1/financial/accounts-payable") return await auditAccounts(params, page, limit);
    if (path === "/v1/financial/accounts-receivable") return { page, limit, total: 0, data: [], synthetic: false };
    if (path === "/v1/sales") return await auditSales(params, page, limit);
    if (path === "/v1/stock") return await auditStock(params, page, limit);
    if (path === "/api/v1/sales/fuel-summary" || path === "/v1/sales/fuel-summary") return await auditFuelSummary(params);
    if (path === "/api/v1/fuel/executive") {
      const fuelSummary = await auditFuelSummary(params);
      const litrosTotal = (fuelSummary || []).reduce((acc, item) => acc + Number(item.litros || 0), 0);
      const combustiveis = (fuelSummary || []).map((item) => ({
        produtoCodigo: item.produtoCodigo || null,
        combustivel: item.combustivel,
        categoria: item.combustivel,
        litros: Number(item.litros || 0),
        participacao: Number(item.participacao || 0),
      }));
      return {
        litrosTotal,
        combustiveis,
        filiais: [],
        ranking: [],
        detalhes: [],
        kpis: {
          litrosVendidos: litrosTotal,
          combustivelLider: combustiveis[0] || { nome: "Sem dados", litros: 0 },
          filialLider: { nomeFilial: "Sem dados", litros: 0 },
          participacaoDiesel: 0,
          participacaoGasolina: 0,
          participacaoEtanol: 0,
        },
      };
    }
    if (path === "/v1/financial/companies") {
      const companies = await auditCompanies(params);
      return { data: companies, total: companies.length, synthetic: false };
    }
  }

  const data = await apiClient.get(path, { params });
  return data?.data || data;
}

function toResultadosByKey(payload, dataKey) {
  const rows = Array.isArray(payload?.[dataKey])
    ? payload[dataKey]
    : Array.isArray(payload?.resultados)
      ? payload.resultados
      : Array.isArray(payload?.data)
        ? payload.data
        : Array.isArray(payload)
          ? payload
          : [];

  return {
    resultados: rows,
    ultimoCodigo: payload?.ultimoCodigo,
    total: payload?.total,
    raw: payload,
  };
}

export async function fetchWebPosto(endpoint, params = {}) {
  const config = WEBPOSTO_ENDPOINT_CONFIG[endpoint];
  if (!config) {
    throw new Error(`Endpoint nao suportado no frontend: ${endpoint}`);
  }

  const data = await get(config.route, params);
  const resolved = toResultadosByKey(data, config.dataKey);
  
  if (endpoint === '/INTEGRACAO/EMPRESAS') validateResponse(resolved.resultados, SCHEMAS.Empresa, endpoint);
  if (endpoint === '/INTEGRACAO/VENDA_ITEM') validateResponse(resolved.resultados, SCHEMAS.VendaItem, endpoint);
  if (endpoint === '/INTEGRACAO/VENDA_FORMA_PAGAMENTO') validateResponse(resolved.resultados, SCHEMAS.VendaFormaPagamento, endpoint);
  if (endpoint === '/INTEGRACAO/CONTA') validateResponse(resolved.resultados, SCHEMAS.Conta, endpoint);

  return resolved;
}

export async function fetchEmpresasRede(params = {}) {
  return fetchWebPosto("/INTEGRACAO/EMPRESAS", params);
}

export function normalizeEmpresaRede(row) {
  return {
    codWeb: row?.codWeb ?? row?.empresaCodigo ?? null,
    empresaCodigo: row?.empresaCodigo ?? null,
    cnpj: row?.cnpj,
    razaoSocial: row?.razao || row?.razaoSocial,
    nomeFantasia: row?.nomeFantasia || row?.fantasia || row?.nome,
    cidade: row?.cidade,
    uf: row?.estado || row?.uf,
    ativo: (row?.statusOperacional || row?.status_operacional || row?.status) !== "INATIVA"
      && (row?.statusOperacional || row?.status_operacional || row?.status) !== "PENDENTE_IDENTIFICACAO",
    status: row?.status,
    statusOperacional: row?.statusOperacional || row?.status_operacional,
    statusDetalhado: row?.statusDetalhado || row?.status_detalhado,
    dataEncerramento: row?.dataEncerramento || null,
    origem: "api",
  };
}

function normalizeEmpresaParam(value) {
  const values = Array.isArray(value)
    ? value
    : String(value || "").trim()
      ? [value]
      : [];
  const filtered = values
    .map((item) => String(item || "").trim())
    .filter((item) => item && !/^(todos|all|__all__)$/i.test(item));
  if (filtered.length === 0) return undefined;
  return filtered.join(",");
}

function baseFilterParams(filters) {
  const empresaCodigoParam = normalizeEmpresaParam(filters.empresaCodigo);

  const centroCusto = Array.isArray(filters.centroCusto)
    ? filters.centroCusto.join(",")
    : filters.centroCusto;
  const tipoDespesa = Array.isArray(filters.tipoDespesa)
    ? filters.tipoDespesa.join(",")
    : filters.tipoDespesa;

  return {
    dataInicial: filters.dataInicial,
    dataFinal: filters.dataFinal,
    empresaCodigo: empresaCodigoParam,
    tipoDespesa,
    centroCusto,
    valorMin: filters.valorMin,
    valorMax: filters.valorMax,
  };
}

function withPaging(filters, page, limit) {
  return {
    ...baseFilterParams(filters),
    page,
    limit,
  };
}

function withCursor(filters, page, limit, ultimoCodigo) {
  return {
    ...withPaging(filters, page, limit),
    ultimoCodigo,
  };
}

function toResultadosEnvelope(data, extras = {}) {
  const resultados = Array.isArray(data?.resultados)
    ? data.resultados
    : Array.isArray(data?.data)
      ? data.data
      : Array.isArray(data)
        ? data
        : [];

  return {
    resultados,
    ultimoCodigo: data?.ultimoCodigo,
    total: data?.total,
    ...extras,
  };
}

export function fetchFinancialOverview(filters) {
  return get("/v1/financial/overview", baseFilterParams(filters));
}

export function fetchFinancialExpenses(filters, page, limit) {
  return get("/v1/financial/expenses", withPaging(filters, page, limit));
}

export function fetchAccountsPayable(filters, page, limit) {
  return get("/v1/financial/accounts-payable", withPaging(filters, page, limit));
}

export function fetchAccountsReceivable(filters, page, limit) {
  return get("/v1/financial/accounts-receivable", withPaging(filters, page, limit));
}

export function fetchSales(filters, page, limit) {
  return get("/v1/sales", withPaging(filters, page, limit));
}

export function fetchStock(filters, page, limit) {
  return get("/v1/stock", withPaging(filters, page, limit));
}

export function fetchCompanies(dataInicial, dataFinal) {
  return get("/v1/financial/companies", {}).then((data) => data.data || []);
}

export function fetchSalesByPayment(filters, page = 1, limit = 50, ultimoCodigo) {
  return get("/v1/sales", withCursor(filters, page, limit, ultimoCodigo)).then((data) =>
    toResultadosEnvelope(data, { consolidado: data?.consolidado || null })
  );
}

export function fetchSalesByItem(filters, page = 1, limit = 50, ultimoCodigo) {
  return get("/v1/sales", withCursor(filters, page, limit, ultimoCodigo)).then((data) =>
    toResultadosEnvelope(data, { consolidado: data?.consolidado || null })
  );
}

export function fetchConta(filters, page = 1, limit = 50, ultimoCodigo) {
  return get("/v1/financial/accounts-payable", withCursor(filters, page, limit, ultimoCodigo)).then((data) =>
    toResultadosEnvelope(data)
  );
}

export function fetchEmpresas(dataInicial, dataFinal, ultimoCodigo) {
  return get("/v1/financial/companies", { dataInicial, dataFinal, ultimoCodigo }).then((data) =>
    toResultadosEnvelope(data, { total: data?.total ?? (data?.data || []).length })
  );
}

// ─── LOGOS SPACE Analytics API (KPIs calculados no backend) ────────────────

function analyticsParams(filters) {
  const empresaCodigo = normalizeEmpresaParam(filters.empresaCodigo);
  const centroCusto = Array.isArray(filters.centroCusto)
    ? filters.centroCusto.join(",")
    : filters.centroCusto || undefined;
  const tipoDespesa = Array.isArray(filters.tipoDespesa)
    ? filters.tipoDespesa.join(",")
    : filters.tipoDespesa || undefined;

  return {
    dataInicial: filters.dataInicial,
    dataFinal: filters.dataFinal,
    empresaCodigo,
    filial: filters.filial || undefined,
    centroCusto,
    tipoDespesa,
    tipoProduto: filters.tipoProduto || undefined,
    grupoProduto: filters.grupoProduto || undefined,
  };
}

function selectedEmpresaCodigos(filters) {
  const values = Array.isArray(filters?.empresaCodigo)
    ? filters.empresaCodigo
    : String(filters?.empresaCodigo || "").trim()
      ? [filters.empresaCodigo]
      : [];
  return values
    .map((value) => String(value || "").replace(/\D/g, ""))
    .filter(Boolean)
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
}

const ANALYTICS_TIMEOUT_MS = 90000;
const COVERAGE_TIMEOUT_MS = 45000;
const SNAPSHOT_TIMEOUT_MS = 8000;
const REFRESH_TIMEOUT_MS = 5000;

function snapshotParams(filters) {
  const empresaCodigo = normalizeEmpresaParam(filters.empresaCodigo);
  const centroCusto = Array.isArray(filters.centroCusto)
    ? filters.centroCusto.join(",")
    : filters.centroCusto || undefined;
  const tipoDespesa = Array.isArray(filters.tipoDespesa)
    ? filters.tipoDespesa.join(",")
    : filters.tipoDespesa || undefined;

  return {
    dataInicial: filters.dataInicial,
    dataFinal: filters.dataFinal,
    empresaCodigo,
    centroCusto,
    tipoDespesa,
  };
}

function toNumber(value) {
  const normalized = Number(String(value ?? 0).replace(",", "."));
  return Number.isFinite(normalized) ? normalized : 0;
}

export async function fetchKpis(filters) {
  if (ENABLE_AUDIT_MODE) {
    return await auditKpis(filters);
  }
  const raw = await apiClient.get("/api/v1/kpis", {
    params: analyticsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchDre(filters) {
  if (ENABLE_AUDIT_MODE) {
    return await auditDre(filters);
  }
  const raw = await apiClient.get("/api/v1/dre", {
    params: analyticsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchDataQuality(filters) {
  if (ENABLE_AUDIT_MODE) {
    return await auditDataQuality(filters);
  }
  const raw = await apiClient.get("/api/v1/data-quality", {
    params: analyticsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFuelSummary(filters) {
  if (ENABLE_AUDIT_MODE) {
    return await auditFuelSummary(filters);
  }
  const raw = await get("/api/v1/sales/fuel-summary", analyticsParams(filters));
  return raw?.data || raw;
}

export async function fetchFuelExecutive(filters) {
  const raw = await apiClient.get("/api/v1/fuel/executive", {
    params: analyticsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFuelSnapshot(filters) {
  const raw = await apiClient.get("/api/v1/fuel/snapshot", {
    params: snapshotParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postFuelRefresh(filters) {
  const raw = await apiClient.post("/api/v1/fuel/refresh", null, {
    params: snapshotParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchProductCatalog(companyCodes = []) {
  const empresaCodigo = Array.isArray(companyCodes) && companyCodes.length > 0
    ? companyCodes.join(",")
    : undefined;
  const raw = await get("/api/v1/products/catalog", { empresaCodigo });
  return raw?.data || raw;
}


export async function fetchFiliaisRede() {
  const raw = await apiClient.get("/api/v1/filiais", { params: {} });
  return raw?.data?.data || raw?.data || [];
}

export async function fetchNetworkCoverage() {
  if (ENABLE_AUDIT_MODE) {
    return await auditNetworkCoverage({});
  }

  const raw = await apiClient.get("/api/v1/network/coverage", { params: {}, timeout: COVERAGE_TIMEOUT_MS });
  return raw?.data || raw;
}

export async function fetchExecutiveSnapshot(filters) {
  const raw = await apiClient.get("/api/v1/executive/snapshot", {
    params: snapshotParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postExecutiveRefresh(filters) {
  const raw = await apiClient.post("/api/v1/executive/refresh", null, {
    params: snapshotParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchSyncControl() {
  const raw = await apiClient.get("/api/v1/sync/control", { params: {} });
  return raw?.data || [];
}

export async function fetchIntegrationLogs(limit = 50) {
  const raw = await apiClient.get("/api/v1/sync/logs", { params: { limit } });
  return raw?.data || [];
}

function financeCenterParams(filters) {
  return baseFilterParams(filters);
}

export async function fetchFinanceCenterSnapshot(filters) {
  const raw = await apiClient.get("/api/v1/finance/center/snapshot", {
    params: financeCenterParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postFinanceCenterRefresh(filters) {
  const raw = await apiClient.post("/api/v1/finance/center/refresh", null, {
    params: financeCenterParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinanceCenterSummary(filters) {
  const raw = await apiClient.get("/api/v1/finance/center/summary", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinanceCenterExpenses(filters, page = 1, limit = 500) {
  const raw = await apiClient.get("/api/v1/finance/center/expenses", {
    params: { ...financeCenterParams(filters), page, limit },
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinanceCenterPayables(filters, page = 1, limit = 500) {
  const raw = await apiClient.get("/api/v1/finance/center/payables", {
    params: { ...financeCenterParams(filters), page, limit },
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinanceCenterReceivables(filters, page = 1, limit = 500) {
  const raw = await apiClient.get("/api/v1/finance/center/receivables", {
    params: { ...financeCenterParams(filters), page, limit },
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinanceCenterBank(filters, page = 1, limit = 500) {
  const raw = await apiClient.get("/api/v1/finance/center/bank-movements", {
    params: { ...financeCenterParams(filters), page, limit },
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinanceCenterCash(filters) {
  const raw = await apiClient.get("/api/v1/finance/center/cash", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinancialIntelligenceSnapshot(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence/snapshot", {
    params: financeCenterParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postFinancialIntelligenceRefresh(filters) {
  const raw = await apiClient.post("/api/v1/finance/intelligence/refresh", null, {
    params: financeCenterParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinancialIntelligence(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinancialHealthScore(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence/health-score", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinancialIntelligenceAdvanced(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence/advanced", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFinancialHealthScoreV3(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence/health-score-v3", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchSupplierIntelligence(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence/suppliers", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchSupplierSegmentation(filters) {
  const raw = await apiClient.get("/api/v1/finance/intelligence/segmentation", {
    params: financeCenterParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

function cashFlowParams(filters) {
  return financeCenterParams(filters);
}

export async function fetchCashFlowSnapshot(filters) {
  const raw = await apiClient.get("/api/v1/finance/cash-flow/snapshot", {
    params: cashFlowParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postCashFlowRefresh(filters) {
  const raw = await apiClient.post("/api/v1/finance/cash-flow/refresh", null, {
    params: cashFlowParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCashFlow(filters) {
  const raw = await apiClient.get("/api/v1/finance/cash-flow", {
    params: cashFlowParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

