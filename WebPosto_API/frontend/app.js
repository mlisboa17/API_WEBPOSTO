import {
  fetchAccountsPayable,
  fetchAccountsReceivable,
  fetchConta,
  fetchCompanies,
  fetchEmpresasRede,
  fetchFinancialExpenses,
  fetchFinancialOverview,
  fetchSales,
  fetchSalesByItem,
  fetchSalesByPayment,
  fetchStock,
  fetchFuelSummary,
  fetchFuelExecutive,
  fetchFuelSnapshot,
  postFuelRefresh,
  fetchProductCatalog,
  fetchFinanceCenterSnapshot,
  postFinanceCenterRefresh,
  fetchFinancialIntelligenceSnapshot,
  postFinancialIntelligenceRefresh,
  fetchFinanceCenterSummary,
  fetchCashFlowSnapshot,
  postCashFlowRefresh,
  fetchCashFlow,
  fetchCashOperationsSnapshot,
  postCashOperationsRefresh,
  fetchCashOperationsAll,
  fetchOperatorPerformanceSnapshot,
  postOperatorPerformanceRefresh,
  fetchOperatorPerformanceAll,
  fetchOperatorIntelligenceCockpit,
  postOperatorIntelligenceRefresh,
  fetchPeopleIntelligenceCockpit,
  postPeopleIntelligenceRefresh,
  fetchPeopleRoiCockpit,
  postPeopleRoiRefresh,
  fetchOperationRoiCockpit,
  postOperationRoiRefresh,
  fetchManagementActionCockpit,
  postManagementActionRefresh,
  fetchGoalsCampaignCockpit,
  postGoalsCampaignRefresh,
  fetchBenchmarkCockpit,
  postBenchmarkRefresh,
  fetchExecutiveScorecardCockpit,
  postExecutiveScorecardRefresh,
  fetchCorporateHubCockpit,
  postCorporateHubRefresh,
} from "./services/api.js";
import { APP_CONFIG } from "./config.js";
import { renderFilters, updateCompanyOptions } from "./components/filters.js";
import { FILIAIS, getFiliaisBaseCodWebSet, hydrateFiliaisCodigoMap, mergeFiliais } from "./components/filiais.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderExpenses } from "./pages/expenses.js";
import { renderAccountsPayable } from "./pages/accountsPayable.js";
import { renderSales } from "./pages/sales.js";
import { renderStock } from "./pages/stock.js";
import { renderExecutiveDashboard } from "./pages/executiveDashboard.js";
import { renderFuelExecutiveDashboard } from "./pages/fuelExecutiveDashboard.js";
import { renderFinanceCenter } from "./pages/financeCenter.js";
import { renderCashFlow } from "./pages/cashFlow.js";
import { renderCashOperations } from "./pages/cashOperations.js";
import { renderOperatorPerformance } from "./pages/operatorPerformance.js";
import { renderPeopleIntelligence } from "./pages/peopleIntelligence.js";
import { renderPeopleRoi } from "./pages/peopleRoi.js";
import { renderOperationRoi } from "./pages/operationRoi.js";
import { renderManagementAction } from "./pages/managementAction.js";
import { renderGoalsCampaign } from "./pages/goalsCampaign.js";
import { renderBenchmark } from "./pages/benchmark.js";
import { renderExecutiveScorecard } from "./pages/executiveScorecard.js";
import { renderCorporateHub } from "./pages/corporateHub.js";
import { renderCompanySwitcher } from "./components/CompanySwitcher.js";
import { createTableState } from "./services/tableState.js";
import {
  ensureProductCatalog,
  enrichFuelExecutive,
  enrichFuelSummary,
  enrichStockRows,
} from "./services/productCatalog.js";

const now = new Date();
const end = now.toISOString().slice(0, 10);
const startDate = new Date(now.getTime() - 1000 * 60 * 60 * 24 * 5)
  .toISOString()
  .slice(0, 10);

const MULTI_FILTER_KEYS = new Set([
  "empresaCodigo",
  "centroCusto",
  "tipoDespesa",
  "expenseNature",
  "expenseManagementGroup",
  "expenseManagementClass",
]);

const VIEW_ALIASES = {
  "finance-center": "financeCenter",
  financecenter: "financeCenter",
  "cash-flow": "cashFlow",
  cashflow: "cashFlow",
  "cash-operations": "cashOperations",
  cashoperations: "cashOperations",
  "operator-performance": "operatorPerformance",
  operatorperformance: "operatorPerformance",
  "people-intelligence": "peopleIntelligence",
  peopleintelligence: "peopleIntelligence",
  "people-roi": "peopleRoi",
  peopleroi: "peopleRoi",
  "operation-roi": "operationRoi",
  operationroi: "operationRoi",
  "management-action": "managementAction",
  managementaction: "managementAction",
  "goals-campaigns": "goalsCampaign",
  goalscampaigns: "goalsCampaign",
  benchmark: "benchmark",
  "benchmark-intelligence": "benchmark",
  "executive-scorecard": "executiveScorecard",
  executivescorecard: "executiveScorecard",
  "corporate-hub": "corporateHub",
  corporatehub: "corporateHub",
};

const VIEW_URL_NAMES = {
  financeCenter: "finance-center",
  cashFlow: "cash-flow",
  cashOperations: "cash-operations",
  operatorPerformance: "operator-performance",
  peopleIntelligence: "people-intelligence",
  peopleRoi: "people-roi",
  operationRoi: "operation-roi",
  managementAction: "management-action",
  goalsCampaign: "goals-campaigns",
  benchmark: "benchmark",
  executiveScorecard: "executive-scorecard",
  corporateHub: "corporate-hub",
};

function normalizeViewId(view) {
  const raw = String(view || "executive").trim();
  return VIEW_ALIASES[raw.toLowerCase()] || raw;
}

function viewForUrl(view) {
  return VIEW_URL_NAMES[view] || view;
}

function normalizeToArray(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item || "").trim())
      .filter(Boolean);
  }
  const text = String(value || "").trim();
  if (!text) return [];
  if (!text.includes(",")) return [text];
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseUrlFilterValue(key, value) {
  if (!MULTI_FILTER_KEYS.has(key)) return value || "";
  const normalized = normalizeToArray(value).filter(
    (item) => !/^(todos|all|__all__)$/i.test(String(item || "").trim())
  );
  if (normalized.length === 0) return "";
  if (normalized.length === 1) return normalized[0];
  return normalized;
}

function serializeUrlFilterValue(key, value) {
  if (value === "" || value === null || value === undefined) return "";
  if (!MULTI_FILTER_KEYS.has(key)) return String(value);
  const normalized = normalizeToArray(value);
  return normalized.join(",");
}

function normalizeEmpresaCodigos(value) {
  return normalizeToArray(value)
    .map((item) => item.replace(/\D/g, ""))
    .filter(Boolean)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item));
}

function fingerprintFilters(filters) {
  const normalized = {
    ...filters,
    empresaCodigo: normalizeToArray(filters?.empresaCodigo),
    centroCusto: normalizeToArray(filters?.centroCusto),
    tipoDespesa: normalizeToArray(filters?.tipoDespesa),
  };
  return JSON.stringify(normalized);
}

function uniqueRowKey(row = {}) {
  const empresa = row.empresaCodigo ?? row.codigoEmpresa ?? row.filialCodigo ?? "";
  const chave =
    row.codigo ??
    row.vendaCodigo ??
    row.vendaItemCodigo ??
    row.tituloPagarCodigo ??
    row.tituloReceberCodigo ??
    row.produtoCodigo ??
    row.caixaCodigo ??
    row.notaEntradaCodigo ??
    "";
  const data = row.data || row.dataMovimento || row.vencimento || row.abertura || "";
  return `${empresa}|${chave}|${data}`;
}

function mergeUniqueRows(rows) {
  const seen = new Set();
  const merged = [];
  rows.forEach((row) => {
    const key = uniqueRowKey(row);
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(row);
  });
  return merged;
}

async function fetchAllPages(fetcher, filters, limit = 200, maxPages = 40) {
  const allRows = [];
  let totalHint = 0;

  for (let page = 1; page <= maxPages; page += 1) {
    const response = await fetcher(filters, page, limit);
    const rows = Array.isArray(response?.data)
      ? response.data
      : Array.isArray(response?.resultados)
        ? response.resultados
        : [];
    const total = Number(response?.total || 0);
    if (total > 0) totalHint = total;
    allRows.push(...rows);

    if (rows.length === 0) break;
    if (total > 0 && allRows.length >= total) break;
    if (rows.length < limit && total === 0) break;
  }

  return {
    data: allRows,
    total: totalHint > 0 ? totalHint : allRows.length,
  };
}

async function fetchDatasetAcrossCompanies(fetcher, filters, displayLimit) {
  const result = await fetchAllPages(fetcher, filters, 200);
  const data = mergeUniqueRows(result.data);
  return {
    page: 1,
    limit: displayLimit,
    total: data.length,
    data,
    synthetic: true,
  };
}

function fromUrl() {
  const query = new URLSearchParams(window.location.search);
  const viewRaw = query.get("view") || "executive";
  const viewNormalized = viewRaw === "fuel" ? "fuels" : normalizeViewId(viewRaw);
  return {
    view: viewNormalized,
    pageExpenses: Number(query.get("pageExpenses") || 1),
    pageAccounts: Number(query.get("pageAccounts") || 1),
    pageSales: Number(query.get("pageSales") || 1),
    pageFuels: Number(query.get("pageFuels") || 1),
    pageStock: Number(query.get("pageStock") || 1),
    filters: {
      dataInicial: query.get("dataInicial") || startDate,
      dataFinal: query.get("dataFinal") || end,
      empresaCodigo: parseUrlFilterValue("empresaCodigo", query.get("empresaCodigo") || ""),
      centroCusto: parseUrlFilterValue("centroCusto", query.get("centroCusto") || ""),
      tipoDespesa: parseUrlFilterValue("tipoDespesa", query.get("tipoDespesa") || ""),
      valorMin: query.get("valorMin") || "",
      valorMax: query.get("valorMax") || "",
      origem: query.get("origem") || "",
      texto: query.get("texto") || "",
      expenseNature: parseUrlFilterValue("expenseNature", query.get("expenseNature") || ""),
      expenseManagementGroup: parseUrlFilterValue(
        "expenseManagementGroup",
        query.get("expenseManagementGroup") || ""
      ),
      expenseManagementClass: parseUrlFilterValue(
        "expenseManagementClass",
        query.get("expenseManagementClass") || ""
      ),
      dreImpact: query.get("dreImpact") || "",
      cashFlowImpact: query.get("cashFlowImpact") || "",
    },
  };
}

function writeUrl(state) {
  const query = new URLSearchParams();
  query.set("view", viewForUrl(state.view));
  query.set("pageExpenses", String(state.pageExpenses));
  query.set("pageAccounts", String(state.pageAccounts));
  query.set("pageSales", String(state.pageSales));
  query.set("pageFuels", String(state.pageFuels));
  query.set("pageStock", String(state.pageStock));

  Object.entries(state.filters).forEach(([key, value]) => {
    const serialized = serializeUrlFilterValue(key, value);
    if (serialized !== "" && serialized !== null && serialized !== undefined) {
      query.set(key, String(serialized));
    }
  });

  const nextUrl = `${window.location.pathname}?${query.toString()}`;
  window.history.replaceState({}, "", nextUrl);
}

function cacheKey(name, payload) {
  return `${name}:${JSON.stringify(payload)}`;
}

function collectEmpresaCodigos(rows) {
  return Array.from(
    new Set(
      (rows || [])
        .map((row) => row?.empresaCodigo)
        .filter((codigo) => codigo !== null && codigo !== undefined && codigo !== "")
        .map((codigo) => String(codigo))
    )
  );
}

function findMissingCodigos(codigos, baseCodigos) {
  return codigos.filter((codigo) => !baseCodigos.has(String(codigo)));
}

function logEndpointDiagnostics(endpoint, payload, baseCodigos) {
  if (!APP_CONFIG.debugWebPosto) return;

  const resultados = Array.isArray(payload?.resultados)
    ? payload.resultados
    : Array.isArray(payload?.data)
      ? payload.data
      : [];
  const codigos = collectEmpresaCodigos(resultados);
  const faltantes = findMissingCodigos(codigos, baseCodigos);

  console.table({
    endpoint,
    total: resultados.length,
    ultimoCodigo: payload?.ultimoCodigo || null,
  });
  console.log(`[REDE DIAG] ${endpoint} empresaCodigo encontrados:`, codigos);
  console.log(`[REDE DIAG] ${endpoint} empresaCodigo fora de filiais.js:`, faltantes);
}

function logRedeValidation(payloads) {
  const baseCodigos = getFiliaisBaseCodWebSet();
  payloads.forEach(({ endpoint, payload }) => logEndpointDiagnostics(endpoint, payload, baseCodigos));
}

const state = {
  ...fromUrl(),
  limitExpenses: 50,
  limitAccounts: 50,
  limitSales: 50,
  limitStock: 50,
  data: {
    overview: null,
    expenses: null,
    accounts: null,
    sales: null,
    stock: null,
    receivables: null,
    fuelSummary: null,
    fuelExecutive: null,
  },
  companies: [],
  productCatalog: null,
  cache: new Map(),
  tables: {
    dashboard: createTableState(),
    expenses: createTableState(),
    accounts: createTableState(),
    sales: createTableState(),
    fuels: createTableState(),
    stock: createTableState(),
  },
};

const loadingNode = document.querySelector("#loading");
const errorNode = document.querySelector("#error");
const executiveNode = document.querySelector("#executiveView");
const dashboardNode = document.querySelector("#dashboardView");
const expensesNode = document.querySelector("#expensesView");
const accountsNode = document.querySelector("#accountsView");
const financeCenterNode = document.querySelector("#financeCenterView");
const cashFlowNode = document.querySelector("#cashFlowView");
const cashOperationsNode = document.querySelector("#cashOperationsView");
const operatorPerformanceNode = document.querySelector("#operatorPerformanceView");
const peopleIntelligenceNode = document.querySelector("#peopleIntelligenceView");
const peopleRoiNode = document.querySelector("#peopleRoiView");
const operationRoiNode = document.querySelector("#operationRoiView");
const managementActionNode = document.querySelector("#managementActionView");
const goalsCampaignNode = document.querySelector("#goalsCampaignView");
const benchmarkNode = document.querySelector("#benchmarkView");
const executiveScorecardNode = document.querySelector("#executiveScorecardView");
const corporateHubNode = document.querySelector("#corporateHubView");
const fuelsNode = document.querySelector("#fuelsView");
const salesNode = document.querySelector("#salesView");
const stockNode = document.querySelector("#stockView");
const filtersNode = document.querySelector("#filtersContainer");

function setLoading(flag) {
  loadingNode.classList.toggle("hidden", !flag);
}

function setError(message) {
  if (!message) {
    errorNode.classList.add("hidden");
    errorNode.textContent = "";
    return;
  }
  errorNode.textContent = message;
  errorNode.classList.remove("hidden");
}

function setView(view) {
  state.view = normalizeViewId(view);
  writeUrl(state);
  mountFilters();
  executiveNode.classList.toggle("hidden", view !== "executive");
  dashboardNode.classList.toggle("hidden", view !== "dashboard");
  expensesNode.classList.toggle("hidden", view !== "expenses");
  accountsNode.classList.toggle("hidden", view !== "accounts");
  financeCenterNode.classList.toggle("hidden", view !== "financeCenter");
  cashFlowNode.classList.toggle("hidden", view !== "cashFlow");
  cashOperationsNode.classList.toggle("hidden", view !== "cashOperations");
  operatorPerformanceNode.classList.toggle("hidden", view !== "operatorPerformance");
  peopleIntelligenceNode.classList.toggle("hidden", view !== "peopleIntelligence");
  peopleRoiNode.classList.toggle("hidden", view !== "peopleRoi");
  operationRoiNode.classList.toggle("hidden", view !== "operationRoi");
  managementActionNode.classList.toggle("hidden", view !== "managementAction");
  goalsCampaignNode.classList.toggle("hidden", view !== "goalsCampaign");
  benchmarkNode.classList.toggle("hidden", view !== "benchmark");
  executiveScorecardNode.classList.toggle("hidden", view !== "executiveScorecard");
  corporateHubNode.classList.toggle("hidden", view !== "corporateHub");
  fuelsNode.classList.toggle("hidden", view !== "fuels");
  salesNode.classList.toggle("hidden", view !== "sales");
  stockNode.classList.toggle("hidden", view !== "stock");

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === view);
  });
}

function ensureDataDefaults() {
  if (!state.data.overview) state.data.overview = null;
  if (!state.data.expenses) state.data.expenses = { resultados: [], data: [] };
  if (!state.data.accounts) state.data.accounts = { resultados: [], data: [] };
  if (!state.data.sales) state.data.sales = { resultados: [], data: [] };
  if (!state.data.stock) state.data.stock = { resultados: [], data: [] };
  if (!state.data.receivables) state.data.receivables = { resultados: [], data: [] };
  if (!state.data.financeCenter) state.data.financeCenter = null;
  if (!state.data.cashFlow) state.data.cashFlow = null;
  if (!state.data.cashOperations) state.data.cashOperations = null;
  if (!state.data.operatorPerformance) state.data.operatorPerformance = null;
  if (!state.data.peopleIntelligence) state.data.peopleIntelligence = null;
  if (!state.data.peopleRoi) state.data.peopleRoi = null;
  if (!state.data.operationRoi) state.data.operationRoi = null;
  if (!state.data.managementAction) state.data.managementAction = null;
  if (!state.data.goalsCampaign) state.data.goalsCampaign = null;
  if (!state.data.benchmark) state.data.benchmark = null;
  if (!state.data.executiveScorecard) state.data.executiveScorecard = null;
  if (!state.data.corporateHub) state.data.corporateHub = null;
}

function clearFilters() {
  state.filters = {
    dataInicial: startDate,
    dataFinal: end,
    empresaCodigo: "",
    centroCusto: "",
    tipoDespesa: "",
    valorMin: "",
    valorMax: "",
    origem: "",
    texto: "",
    expenseNature: "",
    expenseManagementGroup: "",
    expenseManagementClass: "",
    dreImpact: "",
    cashFlowImpact: "",
  };
  state.pageExpenses = 1;
  state.pageAccounts = 1;
  state.pageSales = 1;
  state.pageFuels = 1;
  state.pageStock = 1;
  state.tables.dashboard = createTableState();
  state.tables.expenses = createTableState();
  state.tables.accounts = createTableState();
  state.tables.sales = createTableState();
  state.tables.fuels = createTableState();
  state.tables.stock = createTableState();
  mountFilters();
}

function filterVisibleFieldsForView(view) {
  const base = ["dataInicial", "dataFinal", "empresaCodigo", "centroCusto", "tipoDespesa", "texto", "valorMin", "valorMax"];
  if (view === "expenses") {
    return [
      ...base,
      "expenseNature",
      "expenseManagementGroup",
      "expenseManagementClass",
      "dreImpact",
      "cashFlowImpact",
      "origem",
    ];
  }
  return base;
}

function mountFilters() {
  renderFilters(
    filtersNode,
    state.filters,
    async (nextFilters) => {
      state.filters = nextFilters;
      state.pageExpenses = 1;
      state.pageAccounts = 1;
      state.pageSales = 1;
      state.pageStock = 1;
      writeUrl(state);
      await refreshAll(false);
    },
    async () => {
      clearFilters();
      writeUrl(state);
      await refreshAll(false);
    },
    {
      visibleFields: filterVisibleFieldsForView(state.view),
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    }
  );
  updateCompanyOptions(filtersNode, state.companies, state.filters.empresaCodigo);
}

async function getCached(name, params, loader, bypassCache = false) {
  const key = cacheKey(name, params);
  if (!bypassCache && state.cache.has(key)) {
    return state.cache.get(key);
  }
  const result = await loader();
  state.cache.set(key, result);
  return result;
}

function applyFilialMasterFallback() {
  state.companies = mergeFiliais([]);
  hydrateFiliaisCodigoMap(state.companies);
  updateCompanyOptions(filtersNode, state.companies, state.filters.empresaCodigo);
}

async function refreshCompaniesFromApiInBackground(bypassCache = false) {
  try {
    const empresasRede = await getCached(
      "companies_rede",
      { dataInicial: state.filters.dataInicial, dataFinal: state.filters.dataFinal },
      () => fetchEmpresasRede({ dataInicial: state.filters.dataInicial, dataFinal: state.filters.dataFinal }),
      bypassCache
    );

    const apiRows = empresasRede?.resultados || [];
    state.companies = mergeFiliais(apiRows);

    if (APP_CONFIG.debugWebPosto && apiRows.length < FILIAIS.length) {
      console.warn(
        `API retornou apenas ${apiRows.length} empresas. Base local possui ${FILIAIS.length}. Mesclando dados para visao de rede.`
      );
    }

    const companiesFromBackend = await getCached(
      "companies",
      { dataInicial: state.filters.dataInicial, dataFinal: state.filters.dataFinal },
      () => fetchCompanies(state.filters.dataInicial, state.filters.dataFinal),
      bypassCache
    );

    hydrateFiliaisCodigoMap([...companiesFromBackend, ...state.companies]);
    updateCompanyOptions(filtersNode, state.companies, state.filters.empresaCodigo);

    const companyCodes = state.companies
      .map((company) => Number(company?.empresaCodigo))
      .filter((value) => Number.isFinite(value));
    state.productCatalog = await ensureProductCatalog(fetchProductCatalog, companyCodes);
  } catch (error) {
    console.warn("Falha ao atualizar empresas da API. Mantendo FilialMaster local:", error);
  }
}

async function refreshCompanies(bypassCache = false) {
  applyFilialMasterFallback();
  refreshCompaniesFromApiInBackground(bypassCache);
}

function renderAll() {
  renderExecutiveDashboard(executiveNode, state.data, state.filters);
  
  renderDashboard(dashboardNode, state.data.overview, {
    tableState: state.tables.dashboard,
    onSearchChange: (search) => {
      state.tables.dashboard.search = search;
      renderAll();
    },
    onSortChange: (sort) => {
      state.tables.dashboard.sort = sort;
      renderAll();
    },
    onClearFilters: async () => {
      clearFilters();
      writeUrl(state);
      await refreshAll(false);
    },
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
    exportName: `dashboard_financeiro_${state.filters.dataInicial}`,
  });
  renderExpenses(
    expensesNode,
    state.data.expenses,
    async (nextPage) => {
      state.pageExpenses = nextPage;
      writeUrl(state);
      await refreshExpensesOnly(false);
    },
    {
      tableState: state.tables.expenses,
      onSearchChange: (search) => {
        state.tables.expenses.search = search;
        renderAll();
      },
      onSortChange: (sort) => {
        state.tables.expenses.sort = sort;
        renderAll();
      },
      onClearFilters: async () => {
        clearFilters();
        writeUrl(state);
        await refreshAll(false);
      },
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      exportName: `despesas_${state.filters.dataInicial}`,
    }
  );
  renderAccountsPayable(
    accountsNode,
    state.data.accounts,
    async (nextPage) => {
      state.pageAccounts = nextPage;
      writeUrl(state);
      await refreshAccountsOnly(false);
    },
    {
      tableState: state.tables.accounts,
      onSearchChange: (search) => {
        state.tables.accounts.search = search;
        renderAll();
      },
      onSortChange: (sort) => {
        state.tables.accounts.sort = sort;
        renderAll();
      },
      onClearFilters: async () => {
        clearFilters();
        writeUrl(state);
        await refreshAll(false);
      },
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      exportName: `contas_pagar_${state.filters.dataInicial}`,
    }
  );

  renderSales(
    salesNode,
    state.data.sales,
    async (nextPage) => {
      state.pageSales = nextPage;
      writeUrl(state);
      await refreshSalesOnly(false);
    },
    {
      fuelSummary: state.data.fuelSummary,
      tableState: state.tables.sales,
      onSearchChange: (search) => {
        state.tables.sales.search = search;
        renderAll();
      },
      onSortChange: (sort) => {
        state.tables.sales.sort = sort;
        renderAll();
      },
      onClearFilters: async () => {
        clearFilters();
        writeUrl(state);
        await refreshAll(false);
      },
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      exportName: `vendas_${state.filters.dataInicial}`,
    }
  );

  renderFuelExecutiveDashboard(
    fuelsNode,
    state.data.fuelExecutive,
    {
      tableState: state.tables.fuels,
      onSearchChange: (search) => {
        state.tables.fuels.search = search;
        renderAll();
      },
      onSortChange: (sort) => {
        state.tables.fuels.sort = sort;
        renderAll();
      },
      onClearFilters: async () => {
        clearFilters();
        writeUrl(state);
        await refreshAll(false);
      },
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      exportName: `executivo_combustiveis_${state.filters.dataInicial}`,
    }
  );

  renderFinanceCenter(financeCenterNode, state.data.financeCenter, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderCashFlow(cashFlowNode, state.data.cashFlow, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderCashOperations(cashOperationsNode, state.data.cashOperations, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderOperatorPerformance(operatorPerformanceNode, state.data.operatorPerformance, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderPeopleIntelligence(peopleIntelligenceNode, state.data.peopleIntelligence, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderPeopleRoi(peopleRoiNode, state.data.peopleRoi, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderOperationRoi(operationRoiNode, state.data.operationRoi, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderManagementAction(managementActionNode, state.data.managementAction, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderGoalsCampaign(goalsCampaignNode, state.data.goalsCampaign, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderBenchmark(benchmarkNode, state.data.benchmark, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderExecutiveScorecard(executiveScorecardNode, state.data.executiveScorecard, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderCorporateHub(corporateHubNode, state.data.corporateHub, state.filters, {
    onRefresh: async () => {
      state.cache.clear();
      await refreshAll(true);
    },
  });

  renderStock(
    stockNode,
    state.data.stock,
    async (nextPage) => {
      state.pageStock = nextPage;
      writeUrl(state);
      await refreshStockOnly(false);
    },
    {
      tableState: state.tables.stock,
      onSearchChange: (search) => {
        state.tables.stock.search = search;
        renderAll();
      },
      onSortChange: (sort) => {
        state.tables.stock.sort = sort;
        renderAll();
      },
      onClearFilters: async () => {
        clearFilters();
        writeUrl(state);
        await refreshAll(false);
      },
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      exportName: `estoque_${state.filters.dataInicial}`,
    }
  );
}

async function loadCashOperationsWithSnapshotFirst(bypassCache = false) {
  let snapshot = null;
  try {
    snapshot = await fetchCashOperationsSnapshot(state.filters);
  } catch (error) {
    console.warn("[cashOperations] falha ao carregar snapshot:", error);
  }

  if (snapshot?.operations) {
    state.data.cashOperations = {
      ...snapshot.operations,
      fromSnapshot: snapshot.fromSnapshot,
      lastUpdated: snapshot.lastUpdated,
    };
    if (snapshot.stale) {
      postCashOperationsRefresh(state.filters).catch((error) => {
        console.warn("[cashOperations] refresh em background falhou:", error);
      });
    }
    return;
  }

  const payload = await getCached(
    "cashOperations",
    state.filters,
    () => fetchCashOperationsAll(state.filters),
    bypassCache
  );
  state.data.cashOperations = {
    ...payload,
    fromSnapshot: false,
    lastUpdated: new Date().toISOString(),
  };
  postCashOperationsRefresh(state.filters).catch((error) => {
    console.warn("[cashOperations] refresh em background falhou:", error);
  });
}

async function loadOperatorPerformanceWithSnapshotFirst(bypassCache = false) {
  let snapshot = null;
  try {
    snapshot = await fetchOperatorPerformanceSnapshot(state.filters);
  } catch (error) {
    console.warn("[operatorPerformance] falha ao carregar snapshot:", error);
  }

  const payload = snapshot?.payload || snapshot?.data?.payload;
  if (payload) {
    let intelligence = null;
    try {
      intelligence = await fetchOperatorIntelligenceCockpit(state.filters);
    } catch (error) {
      console.warn("[operatorPerformance] F04 cockpit indisponível:", error);
    }
    state.data.operatorPerformance = {
      ...payload,
      intelligence: intelligence?.cockpit,
      executiveAnswers: intelligence?.executiveAnswers,
      parecerFinal: intelligence?.parecerFinal,
      fromSnapshot: snapshot?.fromSnapshot ?? snapshot?.data?.fromSnapshot ?? true,
      lastUpdated: snapshot?.lastUpdated ?? snapshot?.data?.lastUpdated,
    };
    if (snapshot?.stale ?? snapshot?.data?.stale) {
      postOperatorPerformanceRefresh(state.filters).catch((error) => {
        console.warn("[operatorPerformance] refresh em background falhou:", error);
      });
    }
    return;
  }

  const live = await getCached(
    "operatorPerformance",
    state.filters,
    () => fetchOperatorPerformanceAll(state.filters),
    bypassCache
  );
  let intelligence = null;
  try {
    intelligence = await fetchOperatorIntelligenceCockpit(state.filters);
  } catch (error) {
    console.warn("[operatorPerformance] F04 cockpit indisponível:", error);
  }
  state.data.operatorPerformance = {
    ...live,
    intelligence: intelligence?.cockpit,
    executiveAnswers: intelligence?.executiveAnswers,
    parecerFinal: intelligence?.parecerFinal,
    fromSnapshot: false,
    lastUpdated: new Date().toISOString(),
  };
  postOperatorPerformanceRefresh(state.filters).catch((error) => {
    console.warn("[operatorPerformance] refresh em background falhou:", error);
  });
}

async function loadPeopleIntelligenceWithSnapshotFirst(bypassCache = false) {
  try {
    const intel = await fetchPeopleIntelligenceCockpit(state.filters);
    state.data.peopleIntelligence = {
      cockpit: intel.cockpit,
      executiveAnswers: intel.executiveAnswers,
      parecerFinal: intel.parecerFinal,
      classification: intel.classification,
      fromSnapshot: intel.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (intel.snapshot?.stale) {
      postPeopleIntelligenceRefresh(state.filters).catch((error) => {
        console.warn("[peopleIntelligence] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[peopleIntelligence] falha ao carregar cockpit:", error);
    state.data.peopleIntelligence = null;
  }
}

async function loadOperationRoiWithSnapshotFirst(bypassCache = false) {
  try {
    const roi = await fetchOperationRoiCockpit(state.filters);
    state.data.operationRoi = {
      cockpit: roi.cockpit,
      executiveAnswers: roi.executiveAnswers,
      parecerFinal: roi.parecerFinal,
      qa: roi.qa,
      fromSnapshot: roi.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (roi.snapshot?.stale) {
      postOperationRoiRefresh(state.filters).catch((error) => {
        console.warn("[operationRoi] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[operationRoi] falha ao carregar cockpit:", error);
    state.data.operationRoi = null;
  }
}

async function loadGoalsCampaignWithSnapshotFirst(bypassCache = false) {
  try {
    const gc = await fetchGoalsCampaignCockpit(state.filters);
    state.data.goalsCampaign = {
      cockpit: gc.cockpit,
      executiveAnswers: gc.executiveAnswers,
      parecerFinal: gc.parecerFinal,
      qa: gc.qa,
      fromSnapshot: gc.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (gc.snapshot?.stale) {
      postGoalsCampaignRefresh(state.filters).catch((error) => {
        console.warn("[goalsCampaign] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[goalsCampaign] falha ao carregar cockpit:", error);
    state.data.goalsCampaign = null;
  }
}

async function loadBenchmarkWithSnapshotFirst(bypassCache = false) {
  try {
    const bm = await fetchBenchmarkCockpit(state.filters);
    state.data.benchmark = {
      cockpit: bm.cockpit,
      executiveAnswers: bm.executiveAnswers,
      parecerFinal: bm.parecerFinal,
      qa: bm.qa,
      fromSnapshot: bm.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (bm.snapshot?.stale) {
      postBenchmarkRefresh(state.filters).catch((error) => {
        console.warn("[benchmark] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[benchmark] falha ao carregar cockpit:", error);
    state.data.benchmark = null;
  }
}

async function loadExecutiveScorecardWithSnapshotFirst(bypassCache = false) {
  try {
    const sc = await fetchExecutiveScorecardCockpit(state.filters);
    state.data.executiveScorecard = {
      cockpit: sc.cockpit,
      executiveAnswers: sc.executiveAnswers,
      parecerFinal: sc.parecerFinal,
      decisaoArquitetural: sc.decisaoArquitetural,
      qa: sc.qa,
      fromSnapshot: sc.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (sc.snapshot?.stale) {
      postExecutiveScorecardRefresh(state.filters).catch((error) => {
        console.warn("[executiveScorecard] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[executiveScorecard] falha ao carregar cockpit:", error);
    state.data.executiveScorecard = null;
  }
}

async function loadCorporateHubWithSnapshotFirst(bypassCache = false) {
  try {
    const hub = await fetchCorporateHubCockpit(state.filters);
    state.data.corporateHub = {
      cockpit: hub.cockpit,
      executiveAnswers: hub.executiveAnswers,
      parecerFinal: hub.parecerFinal,
      decisaoArquitetural: hub.decisaoArquitetural,
      qa: hub.qa,
      fromSnapshot: hub.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (hub.snapshot?.stale) {
      postCorporateHubRefresh(state.filters).catch((error) => {
        console.warn("[corporateHub] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[corporateHub] falha ao carregar cockpit:", error);
    state.data.corporateHub = null;
  }
}

async function loadManagementActionWithSnapshotFirst(bypassCache = false) {
  try {
    const mac = await fetchManagementActionCockpit(state.filters);
    state.data.managementAction = {
      cockpit: mac.cockpit,
      executiveAnswers: mac.executiveAnswers,
      parecerFinal: mac.parecerFinal,
      qa: mac.qa,
      fromSnapshot: mac.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (mac.snapshot?.stale) {
      postManagementActionRefresh(state.filters).catch((error) => {
        console.warn("[managementAction] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[managementAction] falha ao carregar cockpit:", error);
    state.data.managementAction = null;
  }
}

async function loadPeopleRoiWithSnapshotFirst(bypassCache = false) {
  try {
    const roi = await fetchPeopleRoiCockpit(state.filters);
    state.data.peopleRoi = {
      cockpit: roi.cockpit,
      executiveAnswers: roi.executiveAnswers,
      parecerFinal: roi.parecerFinal,
      qa: roi.qa,
      fromSnapshot: roi.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (roi.snapshot?.stale) {
      postPeopleRoiRefresh(state.filters).catch((error) => {
        console.warn("[peopleRoi] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[peopleRoi] falha ao carregar cockpit:", error);
    state.data.peopleRoi = null;
  }
}

async function loadCashFlowWithSnapshotFirst(bypassCache = false) {
  let snapshot = null;
  try {
    snapshot = await fetchCashFlowSnapshot(state.filters);
  } catch (error) {
    console.warn("[cashFlow] falha ao carregar snapshot:", error);
  }

  if (snapshot?.fromSnapshot && snapshot?.flow) {
    state.data.cashFlow = {
      ...snapshot.flow,
      fromSnapshot: true,
      lastUpdated: snapshot.lastUpdated,
    };
    postCashFlowRefresh(state.filters).catch((error) => {
      console.warn("[cashFlow] refresh em background falhou:", error);
    });
    return;
  }

  const flow = await getCached(
    "cashFlow",
    state.filters,
    () => fetchCashFlow(state.filters),
    bypassCache
  );
  state.data.cashFlow = {
    ...flow,
    fromSnapshot: false,
    lastUpdated: new Date().toISOString(),
  };
  postCashFlowRefresh(state.filters).catch((error) => {
    console.warn("[cashFlow] refresh em background falhou:", error);
  });
}

async function loadFinanceCenterWithSnapshotFirst(bypassCache = false) {
  let snapshot = null;
  try {
    snapshot = await fetchFinanceCenterSnapshot(state.filters);
  } catch (error) {
    console.warn("[financeCenter] falha ao carregar snapshot:", error);
  }

  if (snapshot?.fromSnapshot && snapshot?.center) {
    state.data.financeCenter = {
      ...snapshot.center,
      fromSnapshot: true,
      lastUpdated: snapshot.lastUpdated,
      warnings: snapshot.warnings || [],
    };
    try {
      const intelSnap = await fetchFinancialIntelligenceSnapshot(state.filters);
      if (intelSnap?.fromSnapshot) {
        state.data.financeCenter.intelligence = intelSnap.intelligence;
        state.data.financeCenter.healthScore = intelSnap.healthScore;
        state.data.financeCenter.advanced = intelSnap.advanced;
        state.data.financeCenter.healthScoreV3 = intelSnap.healthScoreV3;
        state.data.financeCenter.supplierIntelligence = intelSnap.supplierIntelligence;
        state.data.financeCenter.supplierSegmentation = intelSnap.supplierSegmentation;
      }
    } catch (error) {
      console.warn("[financeCenter] intelligence snapshot:", error);
    }
    postFinanceCenterRefresh(state.filters).catch((error) => {
      console.warn("[financeCenter] refresh em background falhou:", error);
    });
    postFinancialIntelligenceRefresh(state.filters).catch((error) => {
      console.warn("[financeCenter] intelligence refresh falhou:", error);
    });
    return;
  }

  const summary = await getCached(
    "financeCenterSummary",
    state.filters,
    () => fetchFinanceCenterSummary(state.filters),
    bypassCache
  );
  state.data.financeCenter = {
    summary,
    fromSnapshot: false,
    lastUpdated: new Date().toISOString(),
  };
  try {
    const intelSnap = await fetchFinancialIntelligenceSnapshot(state.filters);
    if (intelSnap?.fromSnapshot) {
      state.data.financeCenter.intelligence = intelSnap.intelligence;
      state.data.financeCenter.healthScore = intelSnap.healthScore;
      state.data.financeCenter.advanced = intelSnap.advanced;
      state.data.financeCenter.healthScoreV3 = intelSnap.healthScoreV3;
      state.data.financeCenter.supplierIntelligence = intelSnap.supplierIntelligence;
      state.data.financeCenter.supplierSegmentation = intelSnap.supplierSegmentation;
    } else {
      const { fetchFinancialIntelligence, fetchFinancialHealthScore } = await import("./services/api.js");
      state.data.financeCenter.intelligence = await fetchFinancialIntelligence(state.filters);
      state.data.financeCenter.healthScore = await fetchFinancialHealthScore(state.filters);
      try {
        const { fetchFinancialIntelligenceAdvanced, fetchFinancialHealthScoreV3, fetchSupplierIntelligence, fetchSupplierSegmentation } = await import("./services/api.js");
        state.data.financeCenter.advanced = await fetchFinancialIntelligenceAdvanced(state.filters);
        state.data.financeCenter.healthScoreV3 = await fetchFinancialHealthScoreV3(state.filters);
        state.data.financeCenter.supplierIntelligence = await fetchSupplierIntelligence(state.filters);
        state.data.financeCenter.supplierSegmentation = await fetchSupplierSegmentation(state.filters);
      } catch (advErr) {
        console.warn("[financeCenter] advanced live:", advErr);
      }
    }
  } catch (error) {
    console.warn("[financeCenter] intelligence live:", error);
  }
  postFinanceCenterRefresh(state.filters).catch((error) => {
    console.warn("[financeCenter] refresh em background falhou:", error);
  });
}

async function loadFuelWithSnapshotFirst(bypassCache = false) {
  let snapshot = null;
  try {
    snapshot = await fetchFuelSnapshot(state.filters);
  } catch (error) {
    console.warn("[fuels] falha ao carregar snapshot:", error);
  }

  if (snapshot?.fromSnapshot && snapshot?.fuel?.data) {
    state.data.fuelExecutive = enrichFuelExecutive(state.productCatalog, snapshot.fuel.data);
    postFuelRefresh(state.filters).catch((error) => {
      console.warn("[fuels] refresh em background falhou:", error);
    });
    return;
  }

  state.data.fuelExecutive = await getCached(
    "fuelExecutive",
    state.filters,
    () => fetchFuelExecutive(state.filters),
    bypassCache
  );
  state.data.fuelExecutive = enrichFuelExecutive(state.productCatalog, state.data.fuelExecutive);
  postFuelRefresh(state.filters).catch((error) => {
    console.warn("[fuels] refresh em background falhou:", error);
  });
}

async function refreshExecutiveFirst(bypassCache = false) {
  setError("");
  setLoading(true);
  try {
    applyFilialMasterFallback();
    ensureDataDefaults();
    renderAll();
  } catch (err) {
    setError(err.message || "Falha na carga inicial do painel executivo");
  } finally {
    setLoading(false);
  }

  refreshCompaniesFromApiInBackground(bypassCache);
}

async function refreshOperationalDataInBackground(bypassCache = false) {
  try {
    const filtersFingerprintAtCall = fingerprintFilters(state.filters);

    const [overview, expenses, accounts, sales, stock, receivables, salesByItem, salesByPayment, conta] = await Promise.all([
      getCached("overview", state.filters, () => fetchFinancialOverview(state.filters), bypassCache),
      getCached(
        "expenses",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchFinancialExpenses, state.filters, state.limitExpenses),
        bypassCache
      ),
      getCached(
        "accounts",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchAccountsPayable, state.filters, state.limitAccounts),
        bypassCache
      ),
      getCached(
        "sales",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchSales, state.filters, state.limitSales),
        bypassCache
      ),
      getCached(
        "stock",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchStock, state.filters, state.limitStock),
        bypassCache
      ),
      getCached(
        "receivables",
        { ...state.filters, page: 1, limit: 1 },
        () => fetchAccountsReceivable(state.filters, 1, 1),
        bypassCache
      ),
      getCached(
        "salesByItem",
        { ...state.filters, scope: "all" },
        () => fetchSalesByItem(state.filters, state.pageSales, state.limitSales),
        bypassCache
      ),
      getCached(
        "salesByPayment",
        { ...state.filters, scope: "all" },
        () => fetchSalesByPayment(state.filters, state.pageSales, state.limitSales),
        bypassCache
      ),
      getCached(
        "conta",
        { ...state.filters, scope: "all" },
        () => fetchConta(state.filters, state.pageAccounts, state.limitAccounts),
        bypassCache
      ),
    ]);

    if (filtersFingerprintAtCall !== fingerprintFilters(state.filters)) {
      console.log("[BACKGROUND LOAD] Ignorando resultado antigo por alteração de filtros");
      return;
    }

    state.data.overview = overview;
    state.data.expenses = expenses;
    state.data.accounts = accounts;
    state.data.sales = sales;
    state.data.stock = stock;
    state.data.receivables = receivables;

    logRedeValidation([
      { endpoint: "/INTEGRACAO/EMPRESAS", payload: { resultados: state.companies } },
      { endpoint: "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE", payload: expenses },
      { endpoint: "/INTEGRACAO/VENDA", payload: sales },
      { endpoint: "/INTEGRACAO/VENDA_ITEM", payload: salesByItem },
      { endpoint: "/INTEGRACAO/VENDA_FORMA_PAGAMENTO", payload: salesByPayment },
      { endpoint: "/INTEGRACAO/CONTA", payload: conta },
      { endpoint: "/INTEGRACAO/PRODUTO_ESTOQUE", payload: stock },
      { endpoint: "/INTEGRACAO/PRODUTO_EMPRESA", payload: stock },
    ]);

    renderAll();
  } catch (error) {
    console.warn("Falha no carregamento operacional em background:", error);
  }
}

async function refreshAll(bypassCache = false) {
  if (state.view === "executive") {
    await refreshExecutiveFirst(bypassCache);
    refreshOperationalDataInBackground(bypassCache);
    return;
  }

  setError("");
  setLoading(true);
  if (APP_CONFIG.debugFilters) {
    console.log("[debugFilters] filtros globais aplicados", {
      ...state.filters,
      empresaCodigo: normalizeToArray(state.filters.empresaCodigo),
      centroCusto: normalizeToArray(state.filters.centroCusto),
      tipoDespesa: normalizeToArray(state.filters.tipoDespesa),
    });
  }
  try {
    await refreshCompanies(bypassCache);

    ensureDataDefaults();

    if (state.view === "dashboard") {
      state.data.overview = await getCached("overview", state.filters, () => fetchFinancialOverview(state.filters), bypassCache);
    }

    if (state.view === "expenses") {
      state.data.expenses = await getCached(
        "expenses",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchFinancialExpenses, state.filters, state.limitExpenses),
        bypassCache
      );
    }

    if (state.view === "accounts") {
      state.data.accounts = await getCached(
        "accounts",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchAccountsPayable, state.filters, state.limitAccounts),
        bypassCache
      );
    }

    if (state.view === "sales") {
      state.data.sales = await getCached(
        "sales",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchSales, state.filters, state.limitSales),
        bypassCache
      );
      state.data.fuelSummary = await getCached(
        "fuelSummary",
        state.filters,
        () => fetchFuelSummary(state.filters),
        bypassCache
      );
      state.data.fuelSummary = enrichFuelSummary(state.productCatalog, state.data.fuelSummary || []);
    }

    if (state.view === "fuels") {
      await loadFuelWithSnapshotFirst(bypassCache);
    }

    if (state.view === "financeCenter") {
      await loadFinanceCenterWithSnapshotFirst(bypassCache);
    }

    if (state.view === "cashFlow") {
      await loadCashFlowWithSnapshotFirst(bypassCache);
    }

    if (state.view === "cashOperations") {
      await loadCashOperationsWithSnapshotFirst(bypassCache);
    }

    if (state.view === "operatorPerformance") {
      await loadOperatorPerformanceWithSnapshotFirst(bypassCache);
    }

    if (state.view === "peopleIntelligence") {
      await loadPeopleIntelligenceWithSnapshotFirst(bypassCache);
    }

    if (state.view === "peopleRoi") {
      await loadPeopleRoiWithSnapshotFirst(bypassCache);
    }

    if (state.view === "operationRoi") {
      await loadOperationRoiWithSnapshotFirst(bypassCache);
    }

    if (state.view === "managementAction") {
      await loadManagementActionWithSnapshotFirst(bypassCache);
    }

    if (state.view === "goalsCampaign") {
      await loadGoalsCampaignWithSnapshotFirst(bypassCache);
    }

    if (state.view === "benchmark") {
      await loadBenchmarkWithSnapshotFirst(bypassCache);
    }

    if (state.view === "executiveScorecard") {
      await loadExecutiveScorecardWithSnapshotFirst(bypassCache);
    }

    if (state.view === "corporateHub") {
      await loadCorporateHubWithSnapshotFirst(bypassCache);
    }

    if (state.view === "stock") {
      state.data.stock = await getCached(
        "stock",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchStock, state.filters, state.limitStock),
        bypassCache
      );
      state.data.stock = {
        ...state.data.stock,
        data: enrichStockRows(state.productCatalog, state.data.stock?.data || []),
      };
    }

    renderAll();
  } catch (error) {
    setError(error.message || "Falha ao carregar dados financeiros");
  } finally {
    setLoading(false);
  }
}

async function refreshExpensesOnly(bypassCache = false) {
  setError("");
  setLoading(true);
  try {
    const expenses = await getCached(
      "expenses",
      { ...state.filters, scope: "all" },
      () => fetchDatasetAcrossCompanies(fetchFinancialExpenses, state.filters, state.limitExpenses),
      bypassCache
    );
    state.data.expenses = expenses;
    renderAll();
  } catch (error) {
    setError(error.message || "Falha ao carregar despesas");
  } finally {
    setLoading(false);
  }
}

async function refreshAccountsOnly(bypassCache = false) {
  setError("");
  setLoading(true);
  try {
    const accounts = await getCached(
      "accounts",
      { ...state.filters, scope: "all" },
      () => fetchDatasetAcrossCompanies(fetchAccountsPayable, state.filters, state.limitAccounts),
      bypassCache
    );
    state.data.accounts = accounts;
    renderAll();
  } catch (error) {
    setError(error.message || "Falha ao carregar contas a pagar");
  } finally {
    setLoading(false);
  }
}

async function refreshSalesOnly(bypassCache = false) {
  setError("");
  setLoading(true);
  try {
    const sales = await getCached(
      "sales",
      { ...state.filters, scope: "all" },
      () => fetchDatasetAcrossCompanies(fetchSales, state.filters, state.limitSales),
      bypassCache
    );
    state.data.sales = sales;

    state.data.fuelSummary = await getCached(
      "fuelSummary",
      state.filters,
      () => fetchFuelSummary(state.filters),
      bypassCache
    );

    renderAll();
  } catch (error) {
    setError(error.message || "Falha ao carregar vendas");
  } finally {
    setLoading(false);
  }
}

async function refreshStockOnly(bypassCache = false) {
  setError("");
  setLoading(true);
  try {
    const stock = await getCached(
      "stock",
      { ...state.filters, scope: "all" },
      () => fetchDatasetAcrossCompanies(fetchStock, state.filters, state.limitStock),
      bypassCache
    );
    state.data.stock = stock;
    renderAll();
  } catch (error) {
    setError(error.message || "Falha ao carregar estoque");
  } finally {
    setLoading(false);
  }
}

mountFilters();

document.querySelector("#refreshBtn")?.addEventListener("click", async () => {
  state.cache.clear();
  await refreshAll(true);
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", async () => {
    setView(tab.dataset.view);
    await refreshAll(false);
  });
});

setView(state.view);
writeUrl(state);
refreshAll(false);
