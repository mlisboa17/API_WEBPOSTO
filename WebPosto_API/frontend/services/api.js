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
import {
  EXECUTIVE_UNAVAILABLE_MSG,
  normalizeBusinessHealth,
  normalizeCashFlow,
  normalizeDre,
  normalizeFuelExecutive,
  unavailablePayload,
} from './executivePayload.js';

async function executiveGet(path, options = {}) {
  try {
    const raw = await apiClient.get(path, options);
    return {
      data: raw?.data ?? raw,
      snapshot: raw?.snapshot,
      unavailable: false,
    };
  } catch (error) {
    if (error?.unavailable || error?.status === 403 || error?.status === 404) {
      return {
        data: null,
        snapshot: null,
        unavailable: true,
        message: EXECUTIVE_UNAVAILABLE_MSG,
      };
    }
    throw error;
  }
}

async function get(path, params = {}, options = {}) {
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

  const data = await apiClient.get(path, { params, ...options });
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
  const expenseNature = Array.isArray(filters.expenseNature)
    ? filters.expenseNature.join(",")
    : filters.expenseNature;
  const expenseManagementGroup = Array.isArray(filters.expenseManagementGroup)
    ? filters.expenseManagementGroup.join(",")
    : filters.expenseManagementGroup;
  const expenseManagementClass = Array.isArray(filters.expenseManagementClass)
    ? filters.expenseManagementClass.join(",")
    : filters.expenseManagementClass;

  return {
    dataInicial: filters.dataInicial,
    dataFinal: filters.dataFinal,
    empresaCodigo: empresaCodigoParam,
    tipoDespesa,
    centroCusto,
    valorMin: filters.valorMin,
    valorMax: filters.valorMax,
    origem: filters.origem || undefined,
    texto: filters.texto || undefined,
    expenseNature: expenseNature || undefined,
    expenseManagementGroup: expenseManagementGroup || undefined,
    expenseManagementClass: expenseManagementClass || undefined,
    dreImpact: filters.dreImpact || undefined,
    cashFlowImpact: filters.cashFlowImpact || undefined,
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

export async function fetchFinancialOverview(filters) {
  const raw = await apiClient.get("/v1/financial/overview", { params: baseFilterParams(filters) });
  return { data: raw.data, resilience: raw.resilience, success: raw.success !== false };
}

export async function fetchFinancialExpenses(filters, page, limit) {
  const raw = await apiClient.get("/v1/financial/expenses", {
    params: withPaging(filters, page, limit),
    timeout: 45000,
  });
  return { data: raw.data, resilience: raw.resilience, success: raw.success !== false };
}

export function fetchAccountsPayable(filters, page, limit) {
  return get("/v1/financial/accounts-payable", withPaging(filters, page, limit));
}

export function fetchAccountsReceivable(filters, page, limit) {
  return get("/v1/financial/accounts-receivable", withPaging(filters, page, limit));
}

const SALES_REQUEST_TIMEOUT_MS = 45000;

export async function fetchSales(filters, page, limit) {
  const raw = await apiClient.get("/v1/sales", {
    params: withPaging(filters, page, limit),
    timeout: SALES_REQUEST_TIMEOUT_MS,
    allowDegraded: true,
  });
  const payload = raw?.data || raw;
  return {
    ...(payload || {}),
    degraded: Boolean(raw?.degraded),
    resilience: raw?.resilience,
    success: raw?.success !== false,
    source: raw?.source,
  };
}

export function fetchStock(filters, page, limit) {
  return get("/v1/stock", withPaging(filters, page, limit));
}

export function fetchCompanies(dataInicial, dataFinal) {
  return get("/v1/financial/companies", {}).then((data) => data.data || []);
}

export function fetchSalesByPayment(filters, page = 1, limit = 50, ultimoCodigo) {
  return get("/v1/sales", withCursor(filters, page, limit, ultimoCodigo), { timeout: SALES_REQUEST_TIMEOUT_MS }).then((data) =>
    toResultadosEnvelope(data, { consolidado: data?.consolidado || null })
  );
}

export function fetchSalesByItem(filters, page = 1, limit = 50, ultimoCodigo) {
  return get("/v1/sales", withCursor(filters, page, limit, ultimoCodigo), { timeout: SALES_REQUEST_TIMEOUT_MS }).then((data) =>
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

// Sprint 1 — alinhado a ENABLE_OPERATIONAL_ROUTES=false no backend (app.py)
const ENABLE_OPERATIONAL_ROUTES = false;

function deprecatedOperationalMeta(filters = {}) {
  return {
    deprecated: true,
    operational: true,
    empresaCodigo: filters?.empresaCodigo ?? null,
    warnings: ["DEPRECATED - OPERATIONAL — rota desligada no barramento C-Level"],
  };
}

function deprecatedCashOperationsAll(filters = {}) {
  return {
    summary: { total: 0, deprecated: true },
    alerts: { data: [] },
    operators: { data: [] },
    pdvs: { data: [] },
    turns: { data: [] },
    riskScore: { score: 0 },
    fromSnapshot: false,
    lastUpdated: null,
    ...deprecatedOperationalMeta(filters),
  };
}

function deprecatedPerformanceAll(filters = {}) {
  return {
    summary: {},
    operators: { data: [] },
    pdvs: { data: [] },
    turns: { data: [] },
    evolution: [],
    bestPractices: [],
    criticalFocus: [],
    periodo: null,
    fromSnapshot: false,
    lastUpdated: null,
    ...deprecatedOperationalMeta(filters),
  };
}

function deprecatedCockpit(filters = {}) {
  return {
    cockpit: null,
    executiveAnswers: [],
    parecerFinal: null,
    snapshot: { hit: false, stale: true },
    ...deprecatedOperationalMeta(filters),
  };
}

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
    return normalizeDre(await auditDre(filters));
  }
  const result = await executiveGet("/api/v1/dre", {
    params: analyticsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  if (result.unavailable) return unavailablePayload(result.message);
  return normalizeDre(result.data);
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
  const result = await executiveGet("/api/v1/fuel/executive", {
    params: analyticsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  if (result.unavailable) return unavailablePayload(result.message);
  return normalizeFuelExecutive(result.data);
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
  const data = raw?.data || raw;
  if (data?.dre) {
    data.dre = normalizeDre(data.dre);
  }
  return data;
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

export async function fetchDirectorFinancialReconciliation(filters) {
  const raw = await apiClient.get("/api/v1/finance/director-reconciliation", {
    params: financeCenterParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postDirectorFinancialReconciliationRefresh(filters) {
  const raw = await apiClient.post("/api/v1/finance/director-reconciliation/refresh", null, {
    params: financeCenterParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postDepartmentReview(filters, body) {
  const raw = await apiClient.post(
    "/api/v1/finance/director-reconciliation/department-reviews",
    body,
    { params: financeCenterParams(filters), timeout: REFRESH_TIMEOUT_MS },
  );
  return raw?.data || raw;
}

export async function postSharedAllocationRule(filters, body) {
  const raw = await apiClient.post(
    "/api/v1/finance/director-reconciliation/allocation-rules",
    body,
    { params: financeCenterParams(filters), timeout: REFRESH_TIMEOUT_MS },
  );
  return raw?.data || raw;
}

export async function fetchCompleteDepartmentalDre(filters) {
  const raw = await apiClient.get("/api/v1/finance/director-reconciliation/dre-complete", {
    params: financeCenterParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
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
  const result = await executiveGet("/api/v1/finance/cash-flow", {
    params: cashFlowParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  if (result.unavailable) return unavailablePayload(result.message);
  return normalizeCashFlow(result.data);
}

function cashOperationsParams(filters) {
  return financeCenterParams(filters);
}

export async function fetchCashOperationsSnapshot(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { fromSnapshot: false, lastUpdated: null, data: null, ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.get("/api/v1/cash/operations/snapshot", {
    params: cashOperationsParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postCashOperationsRefresh(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { status: "disabled", ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.post("/api/v1/cash/operations/refresh", null, {
    params: cashOperationsParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCashOperationsSummary(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { total: 0, data: [], ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.get("/api/v1/cash/operations/summary", {
    params: cashOperationsParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCashOperationsAll(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return deprecatedCashOperationsAll(filters);
  }
  const [summary, alerts, operators, pdvs, turns, riskScore] = await Promise.all([
    fetchCashOperationsSummary(filters),
    apiClient.get("/api/v1/cash/operations/alerts", { params: cashOperationsParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/cash/operations/operators", { params: cashOperationsParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/cash/operations/pdvs", { params: cashOperationsParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/cash/operations/turns", { params: cashOperationsParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/cash/operations/risk-score", { params: cashOperationsParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
  ]);
  return {
    summary,
    alerts: alerts?.data || alerts,
    operators: operators?.data || operators,
    pdvs: pdvs?.data || pdvs,
    turns: turns?.data || turns,
    riskScore: riskScore?.data || riskScore,
    fromSnapshot: summary?.fromSnapshot,
    lastUpdated: summary?.lastUpdated,
    performanceMs: summary?.performanceMs,
  };
}

function performanceParams(filters) {
  return financeCenterParams(filters);
}

export async function fetchOperatorPerformanceSnapshot(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { fromSnapshot: false, lastUpdated: null, data: null, ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.get("/api/v1/performance/snapshot", {
    params: performanceParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postOperatorPerformanceRefresh(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { status: "disabled", ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.post("/api/v1/performance/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchOperatorPerformanceSummary(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { data: [], ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.get("/api/v1/performance/summary", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchOperatorPerformanceAll(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return deprecatedPerformanceAll(filters);
  }
  const [summaryResp, operatorsResp, pdvsResp, turnsResp] = await Promise.all([
    apiClient.get("/api/v1/performance/summary", { params: performanceParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/performance/operators", { params: performanceParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/performance/pdvs", { params: performanceParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
    apiClient.get("/api/v1/performance/turns", { params: performanceParams(filters), timeout: ANALYTICS_TIMEOUT_MS }),
  ]);
  const summaryBody = summaryResp?.data || summaryResp || {};
  const summaryData = summaryBody?.data || summaryBody;
  return {
    summary: summaryData,
    operators: operatorsResp?.data || operatorsResp,
    pdvs: pdvsResp?.data || pdvsResp,
    turns: turnsResp?.data || turnsResp,
    evolution: summaryData?.evolution,
    bestPractices: summaryData?.bestPractices,
    criticalFocus: summaryData?.criticalFocus,
    periodo: summaryData?.periodo,
    fromSnapshot: summaryBody?.snapshot?.hit,
    lastUpdated: new Date().toISOString(),
  };
}

export async function fetchOperatorIntelligenceSnapshot(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { fromSnapshot: false, lastUpdated: null, data: null, ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.get("/api/v1/operator-intelligence/snapshot", {
    params: performanceParams(filters),
    timeout: SNAPSHOT_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchOperatorIntelligenceCockpit(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return deprecatedCockpit(filters);
  }
  const raw = await apiClient.get("/api/v1/operator-intelligence/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    snapshot: body?.snapshot,
  };
}

export async function postOperatorIntelligenceRefresh(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { status: "disabled", ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.post("/api/v1/operator-intelligence/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchPeopleIntelligenceCockpit(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { ...deprecatedCockpit(filters), classification: null };
  }
  const raw = await apiClient.get("/api/v1/people-intelligence/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    classification: body?.classification,
    snapshot: body?.snapshot,
  };
}

export async function postPeopleIntelligenceRefresh(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { status: "disabled", ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.post("/api/v1/people-intelligence/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchPeopleRoiCockpit(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { ...deprecatedCockpit(filters), qa: [] };
  }
  const raw = await apiClient.get("/api/v1/people-roi/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postPeopleRoiRefresh(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { status: "disabled", ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.post("/api/v1/people-roi/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchOperationRoiCockpit(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { ...deprecatedCockpit(filters), qa: [] };
  }
  const raw = await apiClient.get("/api/v1/operation-roi/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postOperationRoiRefresh(filters) {
  // DEPRECATED - OPERATIONAL
  if (!ENABLE_OPERATIONAL_ROUTES) {
    return { status: "disabled", ...deprecatedOperationalMeta(filters) };
  }
  const raw = await apiClient.post("/api/v1/operation-roi/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchManagementActionCockpit(filters) {
  const raw = await apiClient.get("/api/v1/management-action/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postManagementActionRefresh(filters) {
  const raw = await apiClient.post("/api/v1/management-action/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchGoalsCampaignCockpit(filters) {
  const raw = await apiClient.get("/api/v1/goals-campaigns/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postGoalsCampaignRefresh(filters) {
  const raw = await apiClient.post("/api/v1/goals-campaigns/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchBenchmarkCockpit(filters) {
  const raw = await apiClient.get("/api/v1/benchmark/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postBenchmarkRefresh(filters) {
  const raw = await apiClient.post("/api/v1/benchmark/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchExecutiveScorecardCockpit(filters) {
  const raw = await apiClient.get("/api/v1/executive-scorecard/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    decisaoArquitetural: body?.decisaoArquitetural,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postExecutiveScorecardRefresh(filters) {
  const raw = await apiClient.post("/api/v1/executive-scorecard/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCorporateHubCockpit(filters) {
  const raw = await apiClient.get("/api/v1/corporate-hub/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    decisaoArquitetural: body?.decisaoArquitetural,
    qa: body?.qa,
    snapshot: body?.snapshot,
  };
}

export async function postCorporateHubRefresh(filters) {
  const raw = await apiClient.post("/api/v1/corporate-hub/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchExecutiveDecisionCockpit(filters) {
  const raw = await apiClient.get("/api/v1/executive-decision/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    decisaoArquitetural: body?.decisaoArquitetural,
    qa: body?.qa,
    planoCorporativoConsolidado: body?.planoCorporativoConsolidado,
    snapshot: body?.snapshot,
  };
}

export async function postExecutiveDecisionRefresh(filters) {
  const raw = await apiClient.post("/api/v1/executive-decision/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchActionCenterCockpit(filters) {
  const raw = await apiClient.get("/api/v1/action-center/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    snapshot: body?.snapshot,
  };
}

export async function postActionCenterRefresh(filters) {
  const raw = await apiClient.post("/api/v1/action-center/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchExecutiveCopilotCockpit(filters) {
  const raw = await apiClient.get("/api/v1/executive-copilot/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    conversationLayer: body?.conversationLayer,
    recommendationEngine: body?.recommendationEngine,
    snapshot: body?.snapshot,
  };
}

export async function postExecutiveCopilotRefresh(filters) {
  const raw = await apiClient.post("/api/v1/executive-copilot/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postExecutiveCopilotAsk(filters, pergunta) {
  const raw = await apiClient.post(
    "/api/v1/executive-copilot/ask",
    { pergunta },
    {
      params: performanceParams(filters),
      timeout: ANALYTICS_TIMEOUT_MS,
    }
  );
  const body = raw?.data || raw || {};
  return body?.data || body;
}

export async function fetchAutonomousRecommendationsCockpit(filters) {
  const raw = await apiClient.get("/api/v1/autonomous-recommendations/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    executiveFeedEngine: body?.executiveFeedEngine,
    recommendationPrioritizationEngine: body?.recommendationPrioritizationEngine,
    snapshot: body?.snapshot,
  };
}

export async function postAutonomousRecommendationsRefresh(filters) {
  const raw = await apiClient.post("/api/v1/autonomous-recommendations/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchClosedLoopLearningCockpit(filters) {
  const raw = await apiClient.get("/api/v1/closed-loop-learning/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    executiveFeedbackLoop: body?.executiveFeedbackLoop,
    learningEngine: body?.learningEngine,
    snapshot: body?.snapshot,
  };
}

export async function postClosedLoopLearningRefresh(filters) {
  const raw = await apiClient.post("/api/v1/closed-loop-learning/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchNfceIntelligenceCockpit(filters) {
  const raw = await apiClient.get("/api/v1/nfce-intelligence/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    nfceCatalogEngine: body?.nfceCatalogEngine,
    nfceReconciliationEngine: body?.nfceReconciliationEngine,
    nfceRiskEngine: body?.nfceRiskEngine,
    nfceAnomalyEngine: body?.nfceAnomalyEngine,
    nfceExecutiveIntelligence: body?.nfceExecutiveIntelligence,
    snapshot: body?.snapshot,
  };
}

export async function postNfceIntelligenceRefresh(filters) {
  const raw = await apiClient.post("/api/v1/nfce-intelligence/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchLmcIntelligenceCockpit(filters) {
  const raw = await apiClient.get("/api/v1/lmc-intelligence/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    lmcCatalogEngine: body?.lmcCatalogEngine,
    fuelReconciliationEngine: body?.fuelReconciliationEngine,
    lossSurplusEngine: body?.lossSurplusEngine,
    tankIntelligence: body?.tankIntelligence,
    pumpIntelligence: body?.pumpIntelligence,
    lmcExecutiveIntelligence: body?.lmcExecutiveIntelligence,
    snapshot: body?.snapshot,
  };
}

export async function postLmcIntelligenceRefresh(filters) {
  const raw = await apiClient.post("/api/v1/lmc-intelligence/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFiscalIntelligenceCockpit(filters) {
  const raw = await apiClient.get("/api/v1/fiscal-intelligence/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    productFiscalCatalogEngine: body?.productFiscalCatalogEngine,
    ncmIntelligenceEngine: body?.ncmIntelligenceEngine,
    taxClassificationEngine: body?.taxClassificationEngine,
    financialClassificationEngine: body?.financialClassificationEngine,
    fiscalRiskEngine: body?.fiscalRiskEngine,
    executiveFiscalIntelligence: body?.executiveFiscalIntelligence,
    snapshot: body?.snapshot,
  };
}

export async function postFiscalIntelligenceRefresh(filters) {
  const raw = await apiClient.post("/api/v1/fiscal-intelligence/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFiscalReconciliationCockpit(filters) {
  const raw = await apiClient.get("/api/v1/fiscal-reconciliation/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    fiscalLineageEngine: body?.fiscalLineageEngine,
    nfceVendaReconciliation: body?.nfceVendaReconciliation,
    productSalesReconciliation: body?.productSalesReconciliation,
    lmcSalesReconciliation: body?.lmcSalesReconciliation,
    fiscalFinancialBridge: body?.fiscalFinancialBridge,
    fiscalRiskConsolidation: body?.fiscalRiskConsolidation,
    snapshot: body?.snapshot,
  };
}

export async function postFiscalReconciliationRefresh(filters) {
  const raw = await apiClient.post("/api/v1/fiscal-reconciliation/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchFuelGovernanceCockpit(filters) {
  const raw = await apiClient.get("/api/v1/fuel-governance/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    lmcComplianceAudit: body?.lmcComplianceAudit,
    routineAdherenceAudit: body?.routineAdherenceAudit,
    operationalDisciplineAudit: body?.operationalDisciplineAudit,
    delayAnalysisEngine: body?.delayAnalysisEngine,
    branchComplianceRanking: body?.branchComplianceRanking,
    fuelGovernanceIntelligence: body?.fuelGovernanceIntelligence,
    processoOperacionalSuficiente: body?.processoOperacionalSuficiente,
    snapshot: body?.snapshot,
  };
}

export async function postFuelGovernanceRefresh(filters) {
  const raw = await apiClient.post("/api/v1/fuel-governance/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchNonFuelProductsCockpit(filters) {
  const raw = await apiClient.get("/api/v1/non-fuel-products/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    multiTenantScalabilityEngine: body?.multiTenantScalabilityEngine,
    productDepartmentDiscovery: body?.productDepartmentDiscovery,
    productPerformanceBenchmark: body?.productPerformanceBenchmark,
    residualSkuForensics: body?.residualSkuForensics,
    productLookupOptimization: body?.productLookupOptimization,
    departmentRefinement: body?.departmentRefinement,
    multiBranchProductScale: body?.multiBranchProductScale,
    productMasterCoverage: body?.productMasterCoverage,
    productMatchRecovery: body?.productMatchRecovery,
    departmentIntelligence: body?.departmentIntelligence,
    productRevenueIntelligence: body?.productRevenueIntelligence,
    branchProductMix: body?.branchProductMix,
    salesCoverageReconciliation: body?.salesCoverageReconciliation,
    nonFuelSalesEngine: body?.nonFuelSalesEngine,
    productRankingEngine: body?.productRankingEngine,
    branchDepartmentAnalytics: body?.branchDepartmentAnalytics,
    productSalesLineage: body?.productSalesLineage,
    snapshot: body?.snapshot,
  };
}

export async function postNonFuelProductsRefresh(filters) {
  const raw = await apiClient.post("/api/v1/non-fuel-products/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCommercialExecutionCockpit(filters) {
  const raw = await apiClient.get("/api/v1/commercial-execution/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    commercialAssignmentEngine: body?.commercialAssignmentEngine,
    commercialExecutionTracking: body?.commercialExecutionTracking,
    commercialEvidenceEngine: body?.commercialEvidenceEngine,
    commercialOutcomeMeasurement: body?.commercialOutcomeMeasurement,
    revenueLiftTracking: body?.revenueLiftTracking,
    marginImprovementTracking: body?.marginImprovementTracking,
    commercialPerformance: body?.commercialPerformance,
    snapshot: body?.snapshot,
  };
}

export async function postCommercialExecutionRefresh(filters) {
  const raw = await apiClient.post("/api/v1/commercial-execution/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCommercialLearningCockpit(filters) {
  const raw = await apiClient.get("/api/v1/commercial-learning/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    recommendationEffectivenessEngine: body?.recommendationEffectivenessEngine,
    responsiblePerformanceEngine: body?.responsiblePerformanceEngine,
    branchLearningEngine: body?.branchLearningEngine,
    recommendationCalibrationEngine: body?.recommendationCalibrationEngine,
    outcomeLearningEngine: body?.outcomeLearningEngine,
    executiveLearningReport: body?.executiveLearningReport,
    snapshot: body?.snapshot,
  };
}

export async function postCommercialLearningRefresh(filters) {
  const raw = await apiClient.post("/api/v1/commercial-learning/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchCommercialCopilotCockpit(filters) {
  const raw = await apiClient.get("/api/v1/commercial-copilot/cockpit", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  const body = raw?.data || raw || {};
  return {
    cockpit: body?.data || body?.cockpit,
    executiveAnswers: body?.executiveAnswers,
    parecerFinal: body?.parecerFinal,
    qa: body?.qa,
    governanceRules: body?.governanceRules,
    commercialKnowledgeEngine: body?.commercialKnowledgeEngine,
    commercialReasoningEngine: body?.commercialReasoningEngine,
    commercialRecommendationEngine: body?.commercialRecommendationEngine,
    commercialActionCenterIntegration: body?.commercialActionCenterIntegration,
    commercialConversationLayer: body?.commercialConversationLayer,
    commercialGovernanceLayer: body?.commercialGovernanceLayer,
    snapshot: body?.snapshot,
  };
}

export async function postCommercialCopilotRefresh(filters) {
  const raw = await apiClient.post("/api/v1/commercial-copilot/refresh", null, {
    params: performanceParams(filters),
    timeout: REFRESH_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function postCommercialCopilotAsk(filters, question) {
  const raw = await apiClient.post(
    "/api/v1/commercial-copilot/ask",
    { question },
    {
      params: performanceParams(filters),
      timeout: ANALYTICS_TIMEOUT_MS,
    }
  );
  const body = raw?.data || raw || {};
  return body?.data || body;
}

export function fetchCircuitBreakerStatus() {
  return apiClient.get("/api/v1/admin/circuit-breaker/status");
}

export function resetCircuitBreaker(scope = "global") {
  return apiClient.post("/api/v1/admin/circuit-breaker/reset", { scope });
}

export function fetchFinancialSnapshotHealthCockpit(filters) {
  return apiClient.get("/api/v1/financial/snapshot-health/cockpit", {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialSnapshotHealthInventory() {
  return apiClient.get("/api/v1/financial/snapshot-health/inventory");
}

export function fetchFinancialSnapshotHealthAssessment(filters) {
  return apiClient.get("/api/v1/financial/snapshot-health/assessment", {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialOperationsStatus(filters) {
  return apiClient.get("/api/v1/financial/operations/status", {
    params: baseFilterParams(filters),
  });
}

export function runFinancialOperationsNow(filters) {
  return apiClient.post("/api/v1/financial/operations/run-now", null, {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialOperationsCenterCockpit(filters) {
  return apiClient.get("/api/v1/financial/operations-center/cockpit", {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialOperationsCenterSummary(filters) {
  return apiClient.get("/api/v1/financial/operations-center/summary", {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialOperationsCenterStatus(filters) {
  return apiClient.get("/api/v1/financial/operations-center/status", {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialOperationsCenterAlerts(filters) {
  return apiClient.get("/api/v1/financial/operations-center/alerts", {
    params: baseFilterParams(filters),
  });
}

export function fetchFinancialOperationsCenterExecutions(filters, limit = 50) {
  return apiClient.get("/api/v1/financial/operations-center/executions", {
    params: { ...baseFilterParams(filters), limit },
  });
}

export function fetchFinancialIntelligenceCockpit(filters) {
  return apiClient.get("/api/v1/financial/intelligence-center/cockpit", {
    params: baseFilterParams(filters),
  });
}

export async function fetchCashReconciliationSummary(filters) {
  const raw = await apiClient.get("/api/v1/cash-reconciliation/summary", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return {
    data: raw?.data || raw,
    snapshot: raw?.snapshot,
  };
}

/** CASH-01 — divergência de fechamento Apresentado×Apurado (CASH_CLOSING). */
export async function fetchCashClosingExposure(filters) {
  const raw = await apiClient.get("/api/v1/cash-reconciliation/cash-exposure", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw?.data || raw;
}

export async function fetchOwnerTop5Decisions(filters) {
  // FASE 5: Usar o novo endpoint que suporta pesos de preferência e auditoria
  // Mantemos o fallback caso o novo endpoint não retorne o esperado por algum motivo
  try {
    const raw = await apiClient.get("/api/v1/decisions/top5", {
      params: {
        tenant_id: filters.empresaCodigo || "default",
        empresa_codigo: filters.empresaCodigo || "default",
      },
      timeout: ANALYTICS_TIMEOUT_MS,
    });
    if (raw && raw.success) return raw;
  } catch (error) {
    console.warn("[api] Falha ao buscar Top 5 via Decisions API, tentando fallback:", error);
  }

  // Fallback para o endpoint clássico de snapshot
  const raw = await apiClient.get("/api/v1/owner-action-center/top5", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

export async function fetchBusinessHealth(filters) {
  const result = await executiveGet("/api/v1/owner-action-center/business-health", {
    params: performanceParams(filters),
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  if (result.unavailable) {
    return {
      ...unavailablePayload(result.message),
      snapshot: result.snapshot,
    };
  }
  return normalizeBusinessHealth(result.data);
}

/** Carga única da Tela 1 — top5 + business-health (sem ping duplicado). */
export async function fetchOwnerDiretoriaBundle(filters) {
  const [top5, businessHealth] = await Promise.all([
    fetchOwnerTop5Decisions(filters),
    fetchBusinessHealth(filters),
  ]);
  return {
    ...top5,
    businessHealth,
  };
}

export async function fetchDecisionEvidence(decisionId) {
  const raw = await apiClient.get(`/api/v1/decisions/${encodeURIComponent(decisionId)}/evidence`, {
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

export async function fetchDecisionReviewRequests(decisionId) {
  const raw = await apiClient.get(
    `/api/v1/decisions/${encodeURIComponent(decisionId)}/review-requests`,
    { timeout: ANALYTICS_TIMEOUT_MS },
  );
  return raw;
}

export async function postDecisionReviewRequest(decisionId, body = {}) {
  const raw = await apiClient.post(
    `/api/v1/decisions/${encodeURIComponent(decisionId)}/review-requests`,
    body,
    { timeout: ANALYTICS_TIMEOUT_MS },
  );
  return raw;
}

/** EXEC-02 — Owner clica "Executar Agora": NEW/READY -> EXECUTING. */
export async function executeDecision(decisionId, body = {}) {
  const raw = await apiClient.post(
    `/api/v1/decisions/${encodeURIComponent(decisionId)}/execute`,
    body,
    { timeout: ANALYTICS_TIMEOUT_MS },
  );
  return raw;
}

/** EXEC-02 — Confirmação de resultado (SIM/PARCIALMENTE/NÃO). body.result: 'yes'|'partial'|'no'. */
export async function confirmDecisionResult(decisionId, body) {
  const raw = await apiClient.post(
    `/api/v1/decisions/${encodeURIComponent(decisionId)}/confirm`,
    body,
    { timeout: ANALYTICS_TIMEOUT_MS },
  );
  return raw;
}

/** EXEC-02 — Timeline completa (status, eventos, impacto estimado/confirmado) de uma decisão. */
export async function fetchDecisionTimeline(decisionId) {
  const raw = await apiClient.get(`/api/v1/decisions/${encodeURIComponent(decisionId)}/timeline`, {
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

/** EXEC-03 — Dashboard de métricas de execução (pendentes, hoje, período, all-time) por tenant. */
export async function fetchExecutionMetricsSummary(tenantId, empresaCodigo) {
  const raw = await apiClient.get("/api/v1/decisions/metrics/summary", {
    params: { tenant_id: tenantId, empresa_codigo: empresaCodigo },
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

export async function fetchExecutiveFollowUps(params = {}) {
  const raw = await apiClient.get("/api/v1/executive/follow-ups", {
    params,
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

export async function fetchExecutiveFollowUpDetail(requestId) {
  const raw = await apiClient.get(`/api/v1/executive/follow-ups/${encodeURIComponent(requestId)}`, {
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

export async function fetchFinancialReviewInbox(params = {}) {
  const raw = await apiClient.get("/api/v1/financial/review-inbox", {
    params,
    timeout: ANALYTICS_TIMEOUT_MS,
  });
  return raw;
}

export async function fetchFinancialReviewDetail(requestId) {
  const raw = await apiClient.get(
    `/api/v1/financial/review-inbox/${encodeURIComponent(requestId)}`,
    { timeout: ANALYTICS_TIMEOUT_MS },
  );
  return raw;
}

export async function assignFinancialReview(requestId, responsibleName) {
  const raw = await apiClient.post(
    `/api/v1/financial/review-inbox/${encodeURIComponent(requestId)}/assign`,
    { responsible_name: responsibleName },
    { timeout: ANALYTICS_TIMEOUT_MS },
  );
  return raw;
}

export async function triggerOwnerAnalysisRefresh(filters) {
  return apiClient.post("/api/v1/owner-action-center/analysis/refresh", null, {
    params: performanceParams(filters),
    timeout: 15000,
  });
}
