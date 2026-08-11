import {
  fetchAccountsPayable,
  fetchAccountsReceivable,
  fetchConta,
  fetchCompanies,
  fetchEmpresasRede,
  fetchFinancialExpenses,
  fetchFinancialOverview,
  fetchKpis,
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
  fetchDirectorFinancialReconciliation,
  postDirectorFinancialReconciliationRefresh,
  postDepartmentReview,
  postSharedAllocationRule,
  fetchCompleteDepartmentalDre,
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
  fetchExecutiveDecisionCockpit,
  postExecutiveDecisionRefresh,
  fetchActionCenterCockpit,
  postActionCenterRefresh,
  fetchCashReconciliationSummary,
  fetchCashClosingExposure,
  fetchOwnerDiretoriaBundle,
  fetchDecisionEvidence,
  fetchDecisionReviewRequests,
  postDecisionReviewRequest,
  executeDecision,
  confirmDecisionResult,
  fetchDecisionTimeline,
  fetchExecutionMetricsSummary,
  fetchExecutiveFollowUps,
  fetchExecutiveFollowUpDetail,
  fetchFinancialReviewInbox,
  fetchFinancialReviewDetail,
  assignFinancialReview,
  triggerOwnerAnalysisRefresh,
  fetchExecutiveCopilotCockpit,
  postExecutiveCopilotRefresh,
  postExecutiveCopilotAsk,
  fetchAutonomousRecommendationsCockpit,
  postAutonomousRecommendationsRefresh,
  fetchClosedLoopLearningCockpit,
  postClosedLoopLearningRefresh,
  fetchNfceIntelligenceCockpit,
  postNfceIntelligenceRefresh,
  fetchLmcIntelligenceCockpit,
  postLmcIntelligenceRefresh,
  fetchFiscalIntelligenceCockpit,
  postFiscalIntelligenceRefresh,
  fetchFiscalReconciliationCockpit,
  postFiscalReconciliationRefresh,
  fetchFuelGovernanceCockpit,
  postFuelGovernanceRefresh,
  fetchNonFuelProductsCockpit,
  postNonFuelProductsRefresh,
  fetchCommercialExecutionCockpit,
  postCommercialExecutionRefresh,
  fetchCommercialLearningCockpit,
  postCommercialLearningRefresh,
  fetchCommercialCopilotCockpit,
  postCommercialCopilotRefresh,
  postCommercialCopilotAsk,
  fetchFinancialSnapshotHealthCockpit,
  fetchFinancialOperationsStatus,
  fetchFinancialOperationsCenterCockpit,
  fetchFinancialIntelligenceCockpit,
  runFinancialOperationsNow,
} from "./services/api.js";
import { APP_CONFIG } from "./config.js";
import { renderFilters, updateCompanyOptions } from "./components/filters.js";
import { FILIAIS, getFiliaisBaseCodWebSet, hydrateFiliaisCodigoMap, mergeFiliais } from "./components/filiais.js";
import { renderSales } from "./pages/sales.js";
import { renderStock } from "./pages/stock.js";
import { renderFuelExecutiveDashboard } from "./pages/fuelExecutiveDashboard.js";
import { renderOperatorPerformance } from "./pages/operatorPerformance.js";
import { renderPeopleIntelligence } from "./pages/peopleIntelligence.js";
import { renderPeopleRoi } from "./pages/peopleRoi.js";
import { renderOperationRoi } from "./pages/operationRoi.js";
import { renderManagementAction } from "./pages/managementAction.js";
import { renderGoalsCampaign } from "./pages/goalsCampaign.js";
import { renderBenchmark } from "./pages/benchmark.js";
import { renderExecutiveScorecard } from "./pages/executiveScorecard.js";
import { renderCorporateHub } from "./pages/corporateHub.js";
import { renderExecutiveDecision } from "./pages/executiveDecision.js";
import { renderActionCenter } from "./pages/actionCenter.js";
import { renderCashReconciliation } from "./pages/cashReconciliation.js";
import { renderOwnerDiretoriaHome } from "./pages/ownerDiretoriaHome.js";
import { renderExecutiveFollowUp } from "./pages/executiveFollowUp.js";
import { renderExecutiveFollowUpDetail } from "./pages/executiveFollowUpDetail.js";
import { renderDecisionDetail } from "./pages/decisionDetail.js";
import { renderExecutiveCopilot } from "./pages/executiveCopilot.js";
import { renderRecommendations } from "./pages/recommendations.js";
import { renderLearning } from "./pages/learning.js";
import { renderNfceIntelligence } from "./pages/nfceIntelligence.js";
import { renderLmcIntelligence } from "./pages/lmcIntelligence.js";
import { renderFiscalIntelligence } from "./pages/fiscalIntelligence.js";
import { renderFiscalReconciliation } from "./pages/fiscalReconciliation.js";
import { renderFuelGovernance } from "./pages/fuelGovernance.js";
import { renderCommercialExecution } from "./pages/commercialExecution.js";
import { renderExecutiveWorkspace } from "./pages/executiveWorkspace.js";
import { renderPresidentDashboard } from "./pages/presidentDashboard.js";
import { renderAdministration } from "./pages/administration.js";
import { renderFinancialMonitoring } from "./pages/financialMonitoring.js";
import { renderFinancialOperations } from "./pages/financialOperations.js";
import { renderFinancialOperationsCenter } from "./pages/financialOperationsCenter.js";
import { renderFinancialIntelligence } from "./pages/financialIntelligence.js";
import { renderFinancialHub } from "./pages/financialHub.js";
import { renderFinancialReviewInbox } from "./pages/financialReviewInbox.js";
import { renderFinancialReviewDetail } from "./pages/financialReviewDetail.js";
import { renderTreasuryHub } from "./pages/treasuryHub.js";
import { renderProductsHub } from "./pages/productsHub.js";
import { resolveViewRoute, HUB_VIEWS } from "./services/viewRouting.js";
import {
  getDefaultViewForArea,
  getPresidentDefaultView,
  isPresidentAllowedView,
  isPresidentMode,
  PRESIDENT_MODE_VALUE,
  resolveAreaForView,
} from "./config/navigation.js";
import { mountNavigationShell } from "./components/navigationShell.js";
import { renderCompanySwitcher } from "./components/CompanySwitcher.js";
import { createTableState } from "./services/tableState.js";
import {
  ensureProductCatalog,
  enrichFuelExecutive,
  enrichFuelSummary,
  enrichStockRows,
} from "./services/productCatalog.js";
import { normalizeCashFlow, normalizeFuelExecutive } from "./services/executivePayload.js";
import { buildPresidentDashboardData } from "./services/strategicAnalytics.js";
import { fetchPresidentSnapshotBundle } from "./services/presidentSnapshots.js";

const now = new Date();

function toLocalIsoDate(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const end = toLocalIsoDate(now);
const startDate = toLocalIsoDate(new Date(now.getFullYear(), now.getMonth(), 1));

function resolveRevenueFromSales(salesResult) {
  if (!salesResult) return null;
  const raw = salesResult?.consolidado?.total_vendas;
  if (raw != null && raw !== "") {
    const total = Number(raw);
    if (!Number.isNaN(total)) return total;
  }
  const rows = salesResult?.data || [];
  if (!rows.length) return null;
  return rows.reduce((acc, row) => acc + Number(row?.totalVenda || 0), 0);
}

async function loadRevenueTotal(filters, bypassCache) {
  let salesResult = null;
  try {
    salesResult = await getCached(
      "sales_revenue_hub",
      filters,
      () => fetchSales(filters, 1, 1),
      bypassCache
    );
  } catch (error) {
    console.warn("[revenue] vendas indisponível:", error);
  }

  const fromSales = resolveRevenueFromSales(salesResult);
  const salesDegraded =
    Boolean(salesResult?.degraded) ||
    salesResult?.source === "degraded" ||
    salesResult?.success === false;

  if (fromSales != null && !(fromSales === 0 && salesDegraded)) {
    return fromSales;
  }

  try {
    const kpis = await getCached(
      "kpis_revenue_hub",
      filters,
      () => fetchKpis(filters),
      bypassCache
    );
    const fat = Number(kpis?.faturamento);
    if (!Number.isNaN(fat)) return fat;
  } catch (error) {
    console.warn("[revenue] fallback KPI indisponível:", error);
  }

  if (fromSales === 0 && salesDegraded) return null;
  return fromSales;
}

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
  "executive-decision": "executiveDecision",
  "decision-engine": "executiveDecision",
  decisionengine: "executiveDecision",
  "action-center": "actionCenter",
  actioncenter: "actionCenter",
  "cash-reconciliation": "cashReconciliation",
  cashreconciliation: "cashReconciliation",
  conferencia: "cashReconciliation",
  "conferencia-financeira": "cashReconciliation",
  "executive-copilot": "executiveCopilot",
  executivecopilot: "executiveCopilot",
  copilot: "executiveCopilot",
  recommendations: "recommendations",
  "recommendation-engine": "recommendations",
  recommendationengine: "recommendations",
  learning: "learning",
  "closed-loop-learning": "learning",
  closedlooplearning: "learning",
  nfceIntelligence: "nfceIntelligence",
  "nfce-intelligence": "nfceIntelligence",
  nfceintelligence: "nfceIntelligence",
  lmcIntelligence: "lmcIntelligence",
  "lmc-intelligence": "lmcIntelligence",
  lmcintelligence: "lmcIntelligence",
  fiscalIntelligence: "fiscalIntelligence",
  "fiscal-intelligence": "fiscalIntelligence",
  fiscalintelligence: "fiscalIntelligence",
  fiscalReconciliation: "fiscalReconciliation",
  "fiscal-reconciliation": "fiscalReconciliation",
  fiscalreconciliation: "fiscalReconciliation",
  fuelGovernance: "fuelGovernance",
  "fuel-governance": "fuelGovernance",
  fuelgovernance: "fuelGovernance",
  nonFuelProducts: "nonFuelProducts",
  "non-fuel-products": "nonFuelProducts",
  nonfuelproducts: "nonFuelProducts",
  presidentDashboard: "presidentDashboard",
  "president-dashboard": "presidentDashboard",
  presidentdashboard: "presidentDashboard",
  presidente: "presidentDashboard",
  commercialExecution: "commercialExecution",
  "commercial-execution": "commercialExecution",
  commercialexecution: "commercialExecution",
  commercialLearning: "commercialLearning",
  "commercial-learning": "commercialLearning",
  commerciallearning: "commercialLearning",
  commercialCopilot: "commercialCopilot",
  "commercial-copilot": "commercialCopilot",
  commercialcopilot: "commercialCopilot",
  administration: "administration",
  admin: "administration",
  executiveWorkspace: "executiveWorkspace",
  "executive-workspace": "executiveWorkspace",
  executiveworkspace: "executiveWorkspace",
  workspace: "executiveWorkspace",
  home: "executiveWorkspace",
  diretoria: "ownerDiretoriaHome",
  "owner-diretoria": "ownerDiretoriaHome",
  ownerdiretoriahome: "ownerDiretoriaHome",
  "executive-follow-up": "executiveFollowUp",
  executivefollowup: "executiveFollowUp",
  acompanhamento: "executiveFollowUp",
  "executive-follow-up-detail": "executiveFollowUpDetail",
  executivefollowupdetail: "executiveFollowUpDetail",
  "decision-detail": "decisionDetail",
  decisiondetail: "decisionDetail",
  financialMonitoring: "financialOperationsCenter",
  "financial-monitoring": "financialOperationsCenter",
  financialmonitoring: "financialOperationsCenter",
  financialOperations: "financialOperationsCenter",
  "financial-operations": "financialOperationsCenter",
  financialoperations: "financialOperationsCenter",
  financialOperationsCenter: "financialOperationsCenter",
  "financial-operations-center": "financialOperationsCenter",
  financialoperationscenter: "financialOperationsCenter",
  financialIntelligence: "financialIntelligence",
  "financial-intelligence": "financialIntelligence",
  financialintelligence: "financialIntelligence",
  financialHub: "financialHub",
  "visao-financeira": "financialHub",
  visaofinanceira: "financialHub",
  financialReviewInbox: "financialReviewInbox",
  "financial-review-inbox": "financialReviewInbox",
  financialreviewinbox: "financialReviewInbox",
  conferencias: "financialReviewInbox",
  financialReviewDetail: "financialReviewDetail",
  "financial-review-detail": "financialReviewDetail",
  financialreviewdetail: "financialReviewDetail",
  treasuryHub: "treasuryHub",
  tesouraria: "treasuryHub",
  productsHub: "productsHub",
  "produtos-vendidos": "productsHub",
  "produtos-vendidos-hub": "productsHub",
  produtosvendidos: "productsHub",
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
  executiveDecision: "executive-decision",
  actionCenter: "action-center",
  cashReconciliation: "cash-reconciliation",
  ownerDiretoriaHome: "owner-diretoria",
  executiveFollowUp: "executive-follow-up",
  executiveFollowUpDetail: "executive-follow-up-detail",
  decisionDetail: "decision-detail",
  executiveCopilot: "executive-copilot",
  recommendations: "recommendations",
  learning: "learning",
  nfceIntelligence: "nfce-intelligence",
  lmcIntelligence: "lmc-intelligence",
  fiscalIntelligence: "fiscal-intelligence",
  fiscalReconciliation: "fiscal-reconciliation",
  fuelGovernance: "fuel-governance",
  nonFuelProducts: "non-fuel-products",
  presidentDashboard: "president-dashboard",
  commercialExecution: "commercial-execution",
  commercialLearning: "commercial-learning",
  commercialCopilot: "commercial-copilot",
  administration: "administration",
  executiveWorkspace: "executive-workspace",
  financialMonitoring: "financial-operations-center",
  financialOperations: "financial-operations-center",
  financialOperationsCenter: "financial-operations-center",
  financialIntelligence: "financial-intelligence",
  financialHub: "visao-financeira",
  financialReviewInbox: "financial-review-inbox",
  financialReviewDetail: "financial-review-detail",
  treasuryHub: "tesouraria",
  productsHub: "produtos-vendidos",
};

function normalizeViewId(view) {
  const raw = String(view || "presidentDashboard").trim();
  return VIEW_ALIASES[raw.toLowerCase()] || raw;
}

function applyViewRoute(view, hubTab = "") {
  return resolveViewRoute(normalizeViewId(view), hubTab);
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
  const presidentMode = isPresidentMode(query.get("mode"));
  const viewRaw =
    query.get("view") || (presidentMode ? "owner-diretoria" : "presidentDashboard");
  const hubTab = query.get("hubTab") || "";
  const viewNormalized = viewRaw === "fuel" ? "fuels" : normalizeViewId(viewRaw);
  let route = applyViewRoute(viewNormalized, hubTab);

  if (presidentMode) {
    if (!isPresidentAllowedView(route.view)) {
      route = applyViewRoute(getPresidentDefaultView(), "");
    }
    if (route.view === "treasuryHub" && !route.hubTab) {
      route.hubTab = "fluxo";
    }
  }

  return {
    presidentMode,
    view: route.view,
    hubTab: route.hubTab,
    pageExpenses: Number(query.get("pageExpenses") || 1),
    pageAccounts: Number(query.get("pageAccounts") || 1),
    pageSales: Number(query.get("pageSales") || 1),
    pageFuels: Number(query.get("pageFuels") || 1),
    pageStock: Number(query.get("pageStock") || 1),
    decisionId: query.get("decisionId") || "",
    followUpRequestId: query.get("followUpRequestId") || "",
    financialReviewRequestId: query.get("requestId") || "",
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
  if (state.presidentMode) {
    query.set("mode", PRESIDENT_MODE_VALUE);
  }
  query.set("view", viewForUrl(state.view));
  query.set("pageExpenses", String(state.pageExpenses));
  query.set("pageAccounts", String(state.pageAccounts));
  query.set("pageSales", String(state.pageSales));
  query.set("pageFuels", String(state.pageFuels));
  query.set("pageStock", String(state.pageStock));

  if (state.hubTab && HUB_VIEWS.has(state.view)) {
    query.set("hubTab", state.hubTab);
  }
  if (state.decisionId) {
    query.set("decisionId", state.decisionId);
  }
  if (state.followUpRequestId) {
    query.set("followUpRequestId", state.followUpRequestId);
  }
  if (state.financialReviewRequestId) {
    query.set("requestId", state.financialReviewRequestId);
  }

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

const initialUrlState = fromUrl();

const state = {
  ...initialUrlState,
  area: resolveAreaForView(initialUrlState.view, initialUrlState.presidentMode),
  hubTab: initialUrlState.hubTab || "",
  adminSection: "filiais",
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
    presidentDashboard: null,
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

const decisionReviewUi = {
  loading: false,
  error: null,
  success: null,
};

const decisionExecutionUi = {
  loading: false,
  error: null,
  success: null,
  notYetExecuted: false,
  confirmForm: { result: null },
};

function resetDecisionExecutionUi() {
  decisionExecutionUi.loading = false;
  decisionExecutionUi.error = null;
  decisionExecutionUi.success = null;
  decisionExecutionUi.notYetExecuted = false;
  decisionExecutionUi.confirmForm = { result: null };
}

const sectionUi = {
  overview: { status: "idle", error: null },
  sales: { status: "idle", error: null },
};

function resetSectionUi(key) {
  if (sectionUi[key]) {
    sectionUi[key].status = "idle";
    sectionUi[key].error = null;
  }
}

const financialReviewAssignUi = {
  open: false,
  name: "",
  loading: false,
  error: null,
  success: null,
};

function resetFinancialReviewAssignUi() {
  financialReviewAssignUi.open = false;
  financialReviewAssignUi.name = "";
  financialReviewAssignUi.loading = false;
  financialReviewAssignUi.error = null;
  financialReviewAssignUi.success = null;
}

const loadingNode = document.querySelector("#loading");
const errorNode = document.querySelector("#error");
const presidentDashboardNode = document.querySelector("#presidentDashboardView");
const executiveWorkspaceNode = document.querySelector("#executiveWorkspaceView");
const financialHubNode = document.querySelector("#financialHubView");
const financialReviewInboxNode = document.querySelector("#financialReviewInboxView");
const financialReviewDetailNode = document.querySelector("#financialReviewDetailView");
const treasuryHubNode = document.querySelector("#treasuryHubView");
const productsHubNode = document.querySelector("#productsHubView");
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
const executiveDecisionNode = document.querySelector("#executiveDecisionView");
const actionCenterNode = document.querySelector("#actionCenterView");
const cashReconciliationNode = document.querySelector("#cashReconciliationView");
const ownerDiretoriaHomeNode = document.querySelector("#ownerDiretoriaHomeView");
const executiveFollowUpNode = document.querySelector("#executiveFollowUpView");
const executiveFollowUpDetailNode = document.querySelector("#executiveFollowUpDetailView");
const decisionDetailNode = document.querySelector("#decisionDetailView");
const executiveCopilotNode = document.querySelector("#executiveCopilotView");
const recommendationsNode = document.querySelector("#recommendationsView");
const learningNode = document.querySelector("#learningView");
const nfceIntelligenceNode = document.querySelector("#nfceIntelligenceView");
const lmcIntelligenceNode = document.querySelector("#lmcIntelligenceView");
const fiscalIntelligenceNode = document.querySelector("#fiscalIntelligenceView");
const fiscalReconciliationNode = document.querySelector("#fiscalReconciliationView");
const fuelGovernanceNode = document.querySelector("#fuelGovernanceView");
const nonFuelProductsNode = document.querySelector("#nonFuelProductsView");
const commercialExecutionNode = document.querySelector("#commercialExecutionView");
const commercialLearningNode = document.querySelector("#commercialLearningView");
const commercialCopilotNode = document.querySelector("#commercialCopilotView");
const administrationNode = document.querySelector("#administrationView");
const financialMonitoringNode = document.querySelector("#financialMonitoringView");
const financialOperationsNode = document.querySelector("#financialOperationsView");
const financialOperationsCenterNode = document.querySelector("#financialOperationsCenterView");
const financialIntelligenceNode = document.querySelector("#financialIntelligenceView");
const fuelsNode = document.querySelector("#fuelsView");
const salesNode = document.querySelector("#salesView");
const stockNode = document.querySelector("#stockView");
const filtersNode = document.querySelector("#primaryFiltersHost");

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

function setView(view, options = {}) {
  const normalized = normalizeViewId(view);
  let hubTab = options.hubTab;
  if (hubTab === undefined) {
    if (HUB_VIEWS.has(normalized)) {
      hubTab = state.view === normalized && state.hubTab ? state.hubTab : "";
    } else {
      hubTab = "";
    }
  }
  const route = applyViewRoute(normalized, hubTab);
  if (state.presidentMode) {
    if (!isPresidentAllowedView(route.view)) {
      state.view = getPresidentDefaultView();
      state.hubTab = "";
      state.area = "presidente";
    } else {
      state.view = route.view;
      state.hubTab = route.view === "treasuryHub" ? route.hubTab || "fluxo" : route.hubTab;
      state.area = "presidente";
    }
  } else {
    state.view = route.view;
    state.hubTab = route.hubTab;
    state.area = resolveAreaForView(state.view, false);
  }
  if (options.adminSection) {
    state.adminSection = options.adminSection;
  }
  if (options.decisionId !== undefined) {
    state.decisionId = options.decisionId;
  } else if (state.view !== "decisionDetail") {
    state.decisionId = "";
  }
  if (options.followUpRequestId !== undefined) {
    state.followUpRequestId = options.followUpRequestId;
  } else if (state.view !== "executiveFollowUpDetail") {
    state.followUpRequestId = "";
  }
  if (options.financialReviewRequestId !== undefined) {
    state.financialReviewRequestId = options.financialReviewRequestId;
    resetFinancialReviewAssignUi();
  } else if (route.view !== "financialReviewDetail") {
    state.financialReviewRequestId = "";
    resetFinancialReviewAssignUi();
  }
  writeUrl(state);
  mountFilters();
  mountNavigation();
  document.body.dataset.hubTab = state.hubTab || "";
  const topbarSubtitle = document.querySelector(".topbar p");
  if (topbarSubtitle) {
    topbarSubtitle.textContent = state.presidentMode
      ? "Presidência — decisões, combustível e fluxo de caixa"
      : "Cockpit corporativo — finanças, combustíveis, produtos vendidos e fiscal";
  }
  const activeView = state.view;
  document.body.classList.toggle("president-dashboard-mode", activeView === "presidentDashboard");

  presidentDashboardNode?.classList.toggle("hidden", activeView !== "presidentDashboard");
  executiveWorkspaceNode?.classList.toggle("hidden", activeView !== "executiveWorkspace");
  financialHubNode?.classList.toggle("hidden", activeView !== "financialHub");
  financialReviewInboxNode?.classList.toggle("hidden", activeView !== "financialReviewInbox");
  financialReviewDetailNode?.classList.toggle("hidden", activeView !== "financialReviewDetail");
  treasuryHubNode?.classList.toggle("hidden", activeView !== "treasuryHub");
  productsHubNode?.classList.toggle("hidden", activeView !== "productsHub");
  dashboardNode?.classList.toggle("hidden", activeView !== "dashboard");
  expensesNode.classList.toggle("hidden", activeView !== "expenses");
  accountsNode.classList.toggle("hidden", activeView !== "accounts");
  financeCenterNode.classList.toggle("hidden", activeView !== "financeCenter");
  cashFlowNode.classList.toggle("hidden", activeView !== "cashFlow");
  cashOperationsNode.classList.toggle("hidden", activeView !== "cashOperations");
  operatorPerformanceNode.classList.toggle("hidden", activeView !== "operatorPerformance");
  peopleIntelligenceNode.classList.toggle("hidden", activeView !== "peopleIntelligence");
  peopleRoiNode.classList.toggle("hidden", activeView !== "peopleRoi");
  operationRoiNode.classList.toggle("hidden", activeView !== "operationRoi");
  managementActionNode.classList.toggle("hidden", activeView !== "managementAction");
  goalsCampaignNode.classList.toggle("hidden", activeView !== "goalsCampaign");
  benchmarkNode.classList.toggle("hidden", activeView !== "benchmark");
  executiveScorecardNode.classList.toggle("hidden", activeView !== "executiveScorecard");
  corporateHubNode.classList.toggle("hidden", activeView !== "corporateHub");
  executiveDecisionNode.classList.toggle("hidden", activeView !== "executiveDecision");
  actionCenterNode.classList.toggle("hidden", activeView !== "actionCenter");
  cashReconciliationNode?.classList.toggle("hidden", activeView !== "cashReconciliation");
  ownerDiretoriaHomeNode?.classList.toggle("hidden", activeView !== "ownerDiretoriaHome");
  executiveFollowUpNode?.classList.toggle("hidden", activeView !== "executiveFollowUp");
  executiveFollowUpDetailNode?.classList.toggle("hidden", activeView !== "executiveFollowUpDetail");
  decisionDetailNode?.classList.toggle("hidden", activeView !== "decisionDetail");
  executiveCopilotNode.classList.toggle("hidden", activeView !== "executiveCopilot");
  recommendationsNode.classList.toggle("hidden", activeView !== "recommendations");
  learningNode.classList.toggle("hidden", activeView !== "learning");
  nfceIntelligenceNode.classList.toggle("hidden", activeView !== "nfceIntelligence");
  lmcIntelligenceNode.classList.toggle("hidden", activeView !== "lmcIntelligence");
  fiscalIntelligenceNode.classList.toggle("hidden", activeView !== "fiscalIntelligence");
  fiscalReconciliationNode.classList.toggle("hidden", activeView !== "fiscalReconciliation");
  fuelGovernanceNode.classList.toggle("hidden", activeView !== "fuelGovernance");
  nonFuelProductsNode.classList.toggle("hidden", activeView !== "nonFuelProducts");
  commercialExecutionNode.classList.toggle("hidden", activeView !== "commercialExecution");
  commercialLearningNode.classList.toggle("hidden", activeView !== "commercialLearning");
  commercialCopilotNode.classList.toggle("hidden", activeView !== "commercialCopilot");
  administrationNode.classList.toggle("hidden", activeView !== "administration");
  financialMonitoringNode.classList.toggle("hidden", activeView !== "financialMonitoring");
  financialOperationsNode.classList.toggle("hidden", activeView !== "financialOperations");
  financialOperationsCenterNode.classList.toggle("hidden", activeView !== "financialOperationsCenter");
  financialIntelligenceNode.classList.toggle("hidden", activeView !== "financialIntelligence");
  fuelsNode.classList.toggle("hidden", activeView !== "fuels");
  salesNode.classList.toggle("hidden", activeView !== "sales");
  stockNode.classList.toggle("hidden", activeView !== "stock");
}

function mountNavigation() {
  mountNavigationShell({
    areaId: state.area,
    view: state.view,
    presidentMode: state.presidentMode,
    onAreaChange: async (areaId) => {
      state.area = areaId;
      const nextView = getDefaultViewForArea(areaId, state.presidentMode);
      if (state.presidentMode) {
        const hubTab = nextView === "treasuryHub" ? "fluxo" : "";
        setView(nextView, { hubTab });
      } else if (areaId === "administracao") {
        setView("administration", { adminSection: "filiais" });
      } else {
        setView(nextView);
      }
      await refreshAll(false);
    },
    onTabChange: async (view, tabId, hubTab = "") => {
      if (state.presidentMode) {
        setView(view, { hubTab: hubTab || (view === "treasuryHub" ? "fluxo" : "") });
        await refreshAll(false);
        return;
      }
      if (state.area === "administracao" && view !== "financialOperationsCenter") {
        setView("administration", { adminSection: tabId || "filiais" });
      } else {
        setView(view);
      }
      await refreshAll(false);
    },
    onMotorChange: async (view) => {
      setView(view);
      await refreshAll(false);
    },
  });
}

function ensureDataDefaults() {
  if (!state.data.overview) state.data.overview = null;
  if (state.data.overviewResilience === undefined) state.data.overviewResilience = null;
  if (!state.data.expenses) state.data.expenses = { resultados: [], data: [] };
  if (state.data.expensesResilience === undefined) state.data.expensesResilience = null;
  if (state.data.receivablesTotal === undefined) state.data.receivablesTotal = null;
  if (state.data.revenueTotal === undefined) state.data.revenueTotal = null;
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
  if (!state.data.executiveDecision) state.data.executiveDecision = null;
  if (!state.data.actionCenter) state.data.actionCenter = null;
  if (!state.data.cashReconciliation) state.data.cashReconciliation = null;
  if (!state.data.ownerDiretoriaHome) state.data.ownerDiretoriaHome = null;
  if (!state.data.decisionDetail) state.data.decisionDetail = null;
  if (!state.data.decisionReviewRequests) state.data.decisionReviewRequests = null;
  if (!state.data.decisionExecution) state.data.decisionExecution = null;
  if (!state.data.executiveFollowUp) state.data.executiveFollowUp = null;
  if (!state.data.executiveFollowUpDetail) state.data.executiveFollowUpDetail = null;
  if (!state.data.financialReviewInbox) state.data.financialReviewInbox = null;
  if (!state.data.financialReviewDetail) state.data.financialReviewDetail = null;
  if (!state.data.executiveCopilot) state.data.executiveCopilot = null;
  if (!state.data.recommendations) state.data.recommendations = null;
  if (!state.data.learning) state.data.learning = null;
  if (!state.data.nfceIntelligence) state.data.nfceIntelligence = null;
  if (!state.data.lmcIntelligence) state.data.lmcIntelligence = null;
  if (!state.data.fiscalIntelligence) state.data.fiscalIntelligence = null;
  if (!state.data.fiscalReconciliation) state.data.fiscalReconciliation = null;
  if (!state.data.fuelGovernance) state.data.fuelGovernance = null;
  if (!state.data.nonFuelProducts) state.data.nonFuelProducts = null;
  if (!state.data.commercialExecution) state.data.commercialExecution = null;
  if (!state.data.commercialLearning) state.data.commercialLearning = null;
  if (!state.data.commercialCopilot) state.data.commercialCopilot = null;
  if (!state.data.financialMonitoring) state.data.financialMonitoring = null;
  if (!state.data.financialOperations) state.data.financialOperations = null;
  if (!state.data.financialOperationsCenter) state.data.financialOperationsCenter = null;
  if (!state.data.financialIntelligence) state.data.financialIntelligence = null;
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
  const base = ["periodo", "empresaCodigo", "centroCusto", "tipoDespesa", "texto", "valorMin", "valorMax"];
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

async function navigateToView(view) {
  const route = applyViewRoute(view);
  setView(route.view, { hubTab: route.hubTab });
  await refreshAll(false);
}

function renderAll() {
  const activeView = state.view;

  if (activeView === "presidentDashboard") {
    renderPresidentDashboard(presidentDashboardNode, state.data.presidentDashboard, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      onNavigate: navigateToView,
    });
  }

  if (activeView === "executiveWorkspace") {
    renderExecutiveWorkspace(executiveWorkspaceNode, buildWorkspaceDataPayload(), state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      onNavigate: navigateToView,
      companies: state.companies,
    });
  }

  if (activeView === "financialHub") {
    renderFinancialHub(financialHubNode, {
      activeTab: state.hubTab || "receitas",
      data: {
        overview: state.data.overview,
        overviewResilience: state.data.overviewResilience,
        expenses: state.data.expenses,
        expensesResilience: state.data.expensesResilience,
        revenueTotal: state.data.revenueTotal,
      },
      filters: state.filters,
      companies: state.companies,
      options: {
        onTabChange: async (tab) => {
          state.hubTab = tab;
          writeUrl(state);
          await refreshAll(false);
        },
        onPageChange: async (nextPage) => {
          state.pageExpenses = nextPage;
          writeUrl(state);
          await refreshExpensesOnly(false);
        },
        receitas: {
          tableState: state.tables.dashboard,
          onNavigate: navigateToView,
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
        },
        despesas: {
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
        },
      },
    });
  }

  if (activeView === "treasuryHub") {
    renderTreasuryHub(treasuryHubNode, {
      activeTab: state.hubTab || "fluxo",
      data: {
        cashFlow: state.data.cashFlow,
        accounts: state.data.accounts,
        cashOperations: state.data.cashOperations,
        financeCenter: state.data.financeCenter,
      },
      filters: state.filters,
      companies: state.companies,
      options: {
        onTabChange: async (tab) => {
          state.hubTab = tab;
          writeUrl(state);
          await refreshAll(false);
        },
        onAccountsPageChange: async (nextPage) => {
          state.pageAccounts = nextPage;
          writeUrl(state);
          await refreshAccountsOnly(false);
        },
        fluxo: {
          onRefresh: async () => {
            state.cache.clear();
            await refreshAll(true);
          },
        },
        extratos: {
          onRefresh: async () => {
            state.cache.clear();
            await refreshAll(true);
          },
        },
        conciliacao: {
          onRefresh: async () => {
            state.cache.clear();
            await refreshAll(true);
          },
          onDepartmentReview: async (body) => {
            const result = await postDepartmentReview(state.filters, body);
            state.data.financeCenter.directorReconciliation = result.reconciliation;
            if (result.reconciliation?.publication?.dreTotalsReleased) {
              state.data.financeCenter.completeDepartmentalDre = await fetchCompleteDepartmentalDre(state.filters);
            }
            renderAll();
          },
          onSharedAllocation: async (body) => {
            const result = await postSharedAllocationRule(state.filters, body);
            state.data.financeCenter.directorReconciliation = result.reconciliation;
            if (result.reconciliation?.publication?.dreTotalsReleased) {
              state.data.financeCenter.completeDepartmentalDre = await fetchCompleteDepartmentalDre(state.filters);
            }
            renderAll();
          },
        },
        accounts: {
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
        },
      },
    });
  }

  if (activeView === "productsHub") {
    renderProductsHub(productsHubNode, {
      activeTab: state.hubTab || "mix",
      data: {
        nonFuelProducts: state.data.nonFuelProducts,
        commercialCopilot: state.data.commercialCopilot,
        commercialLearning: state.data.commercialLearning,
      },
      filters: state.filters,
      companies: state.companies,
      options: {
        onTabChange: async (tab) => {
          state.hubTab = tab;
          writeUrl(state);
          await refreshAll(false);
        },
        onNavigate: navigateToView,
        onCopilotAsk: async (question) => postCommercialCopilotAsk(state.filters, question),
        mix: {
          onRefresh: async () => {
            state.cache.clear();
            await refreshAll(true);
          },
        },
        oportunidades: {
          onRefresh: async () => {
            state.cache.clear();
            await refreshAll(true);
          },
        },
        performance: {
          onRefresh: async () => {
            state.cache.clear();
            await refreshAll(true);
          },
        },
      },
    });
  }

  if (activeView === "sales") {
    renderSales(
      salesNode,
      state.data.sales,
      async (nextPage) => {
        state.pageSales = nextPage;
        writeUrl(state);
        await refreshSalesOnly(false);
      },
      {
        filters: state.filters,
        companies: state.companies,
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
  }

  if (activeView === "fuels") {
    renderFuelExecutiveDashboard(
      fuelsNode,
      state.data.fuelExecutive,
      {
        tableState: state.tables.fuels,
        companies: state.companies,
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
  }

  if (activeView === "operatorPerformance") {
    renderOperatorPerformance(operatorPerformanceNode, state.data.operatorPerformance, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    });
  }

  if (activeView === "peopleIntelligence") {
    renderPeopleIntelligence(peopleIntelligenceNode, state.data.peopleIntelligence, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    });
  }

  if (activeView === "peopleRoi") {
    renderPeopleRoi(peopleRoiNode, state.data.peopleRoi, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    });
  }

  if (activeView === "operationRoi") {
    renderOperationRoi(operationRoiNode, state.data.operationRoi, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    });
  }

  if (activeView === "managementAction") {
    renderManagementAction(managementActionNode, state.data.managementAction, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    });
  }

  if (activeView === "goalsCampaign") {
    renderGoalsCampaign(goalsCampaignNode, state.data.goalsCampaign, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
    });
  }

  if (activeView === "benchmark") {
    renderBenchmark(benchmarkNode, state.data.benchmark, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "executiveScorecard") {
    renderExecutiveScorecard(executiveScorecardNode, state.data.executiveScorecard, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "corporateHub") {
    renderCorporateHub(corporateHubNode, state.data.corporateHub, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "executiveDecision") {
    renderExecutiveDecision(executiveDecisionNode, state.data.executiveDecision, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "actionCenter") {
    renderActionCenter(actionCenterNode, state.data.actionCenter, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "cashReconciliation") {
    renderCashReconciliation(cashReconciliationNode, state.data.cashReconciliation, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "ownerDiretoriaHome") {
    renderOwnerDiretoriaHome(ownerDiretoriaHomeNode, state.data.ownerDiretoriaHome, state.filters, {
      followUpPayload: state.data.executiveFollowUp,
      onRefresh: async () => {
        state.cache.clear();
        await loadOwnerDiretoriaHome(true);
        renderAll();
      },
      onOpenDecision: (decisionId) => {
        resetDecisionExecutionUi();
        setView("decisionDetail", { decisionId });
        loadDecisionDetail(decisionId).then(() => renderAll());
      },
      onOpenFollowUp: (requestId) => {
        setView("executiveFollowUpDetail", { followUpRequestId: requestId });
        loadExecutiveFollowUpDetail(requestId).then(() => renderAll());
      },
    });
  }

  if (activeView === "executiveFollowUp") {
    renderExecutiveFollowUp(executiveFollowUpNode, state.data.executiveFollowUp, state.filters, {
      onRefresh: async () => {
        await loadExecutiveFollowUp(true);
        renderAll();
      },
      onOpenFollowUp: (requestId) => {
        setView("executiveFollowUpDetail", { followUpRequestId: requestId });
        loadExecutiveFollowUpDetail(requestId).then(() => renderAll());
      },
    });
  }

  if (activeView === "executiveFollowUpDetail") {
    renderExecutiveFollowUpDetail(
      executiveFollowUpDetailNode,
      state.data.executiveFollowUpDetail,
      state.filters,
      {
        onBack: () => {
          setView("executiveFollowUp");
          renderAll();
        },
        onRefresh: async () => {
          if (state.followUpRequestId) {
            await loadExecutiveFollowUpDetail(state.followUpRequestId, true);
            renderAll();
          }
        },
        onOpenDecision: (decisionId) => {
          setView("decisionDetail", { decisionId });
          loadDecisionDetail(decisionId).then(() => renderAll());
        },
      },
    );
  }

  if (activeView === "decisionDetail") {
    const preferenceAudit = state.data.ownerDiretoriaHome?.data?.preference_audit;
    renderDecisionDetail(decisionDetailNode, state.data.decisionDetail, state.filters, {
      decisionId: state.decisionId,
      preferenceAudit,
      reviewRequests: state.data.decisionReviewRequests,
      reviewLoading: decisionReviewUi.loading,
      reviewError: decisionReviewUi.error,
      reviewSuccess: decisionReviewUi.success,
      execution: state.data.decisionExecution,
      executionUi: decisionExecutionUi,
      executionMetrics: state.data.executionMetrics,
      onBack: () => {
        resetDecisionExecutionUi();
        setView("ownerDiretoriaHome");
        renderAll();
      },
      onRefresh: async () => {
        if (state.decisionId) {
          decisionReviewUi.error = null;
          decisionReviewUi.success = null;
          await loadDecisionDetail(state.decisionId, true);
          renderAll();
        }
      },
      onRequestReview: async () => {
        if (!state.decisionId || decisionReviewUi.loading) return;
        decisionReviewUi.loading = true;
        decisionReviewUi.error = null;
        decisionReviewUi.success = null;
        renderAll();
        try {
          const resp = await postDecisionReviewRequest(state.decisionId, {
            request_type: "NOMINAL_IDENTIFICATION_REVIEW",
          });
          if (resp?.success && resp?.data) {
            decisionReviewUi.success = resp.data.message || "Conferência solicitada";
            await loadDecisionDetail(state.decisionId, true);
            await loadExecutiveFollowUp(true);
          } else {
            decisionReviewUi.error = "Não foi possível solicitar conferência.";
          }
        } catch (error) {
          decisionReviewUi.error =
            error?.response?.data?.detail ||
            error?.message ||
            "Não foi possível solicitar conferência.";
        } finally {
          decisionReviewUi.loading = false;
          renderAll();
        }
      },
      onExecuteDecision: async () => {
        if (!state.decisionId || decisionExecutionUi.loading) return;
        decisionExecutionUi.loading = true;
        decisionExecutionUi.error = null;
        decisionExecutionUi.success = null;
        renderAll();
        try {
          await executeDecision(state.decisionId, { user_id: "owner" });
          decisionExecutionUi.success = "Execução iniciada";
          await loadDecisionExecution(state.decisionId);
        } catch (error) {
          decisionExecutionUi.error =
            error?.response?.data?.detail || error?.message || "Não foi possível executar a decisão.";
        } finally {
          decisionExecutionUi.loading = false;
          renderAll();
        }
      },
      onSelectConfirmResult: (result) => {
        decisionExecutionUi.confirmForm = { result };
        renderAll();
      },
      onConfirmDecision: async ({ result, confirmedAmount, partialProgress, partialReason, rejectionReason }) => {
        if (!state.decisionId || decisionExecutionUi.loading || !result) return;
        decisionExecutionUi.loading = true;
        decisionExecutionUi.error = null;
        decisionExecutionUi.success = null;
        renderAll();
        try {
          await confirmDecisionResult(state.decisionId, {
            user_id: "owner",
            result,
            confirmed_amount: confirmedAmount,
            partial_progress: partialProgress,
            partial_reason: partialReason,
            rejection_reason: rejectionReason,
          });
          decisionExecutionUi.success = "Confirmação registrada";
          decisionExecutionUi.confirmForm = { result: null };
          await loadDecisionExecution(state.decisionId);
        } catch (error) {
          decisionExecutionUi.error =
            error?.response?.data?.detail || error?.message || "Não foi possível confirmar o resultado.";
        } finally {
          decisionExecutionUi.loading = false;
          renderAll();
        }
      },
    });
  }

  if (activeView === "financialReviewInbox") {
    renderFinancialReviewInbox(financialReviewInboxNode, state.data.financialReviewInbox, state.filters, {
      onRefresh: async () => {
        await loadFinancialReviewInbox(true);
        renderAll();
      },
      onOpenReview: (requestId) => {
        setView("financialReviewDetail", { financialReviewRequestId: requestId });
        loadFinancialReviewDetail(requestId).then(() => renderAll());
      },
    });
  }

  if (activeView === "financialReviewDetail") {
    renderFinancialReviewDetail(
      financialReviewDetailNode,
      state.data.financialReviewDetail,
      state.filters,
      {
        assignState: financialReviewAssignUi,
        onBack: () => {
          resetFinancialReviewAssignUi();
          setView("financialReviewInbox");
          renderAll();
        },
        onRefresh: async () => {
          if (state.financialReviewRequestId) {
            await loadFinancialReviewDetail(state.financialReviewRequestId, true);
            renderAll();
          }
        },
        onAssignOpen: () => {
          financialReviewAssignUi.open = true;
          financialReviewAssignUi.error = null;
          renderAll();
        },
        onAssignCancel: () => {
          financialReviewAssignUi.open = false;
          financialReviewAssignUi.error = null;
          renderAll();
        },
        onAssignConfirm: async (name) => {
          if (!state.financialReviewRequestId) return;
          if (!name) {
            financialReviewAssignUi.error = "Informe o nome do responsável.";
            renderAll();
            return;
          }
          financialReviewAssignUi.loading = true;
          financialReviewAssignUi.error = null;
          financialReviewAssignUi.success = null;
          renderAll();
          try {
            const response = await assignFinancialReview(state.financialReviewRequestId, name);
            await loadFinancialReviewDetail(state.financialReviewRequestId, true);
            await loadFinancialReviewInbox(true);
            financialReviewAssignUi.open = false;
            financialReviewAssignUi.loading = false;
            financialReviewAssignUi.success =
              response?.message || "Conferência atribuída com sucesso.";
            renderAll();
          } catch (error) {
            financialReviewAssignUi.loading = false;
            financialReviewAssignUi.error =
              error?.response?.data?.detail ||
              error?.message ||
              "Não foi possível assumir esta conferência.";
            renderAll();
          }
        },
      },
    );
  }

  if (activeView === "executiveCopilot") {
    renderExecutiveCopilot(executiveCopilotNode, state.data.executiveCopilot, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      onAsk: async (pergunta) => postExecutiveCopilotAsk(state.filters, pergunta),
      companies: state.companies,
    });
  }

  if (activeView === "recommendations") {
    renderRecommendations(recommendationsNode, state.data.recommendations, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "learning") {
    renderLearning(learningNode, state.data.learning, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "nfceIntelligence") {
    renderNfceIntelligence(nfceIntelligenceNode, state.data.nfceIntelligence, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      onNavigate: navigateToView,
      companies: state.companies,
    });
  }

  if (activeView === "lmcIntelligence") {
    renderLmcIntelligence(lmcIntelligenceNode, state.data.lmcIntelligence, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "fiscalIntelligence") {
    renderFiscalIntelligence(fiscalIntelligenceNode, state.data.fiscalIntelligence, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      onNavigate: navigateToView,
      companies: state.companies,
    });
  }

  if (activeView === "fiscalReconciliation") {
    renderFiscalReconciliation(fiscalReconciliationNode, state.data.fiscalReconciliation, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      onNavigate: navigateToView,
      companies: state.companies,
    });
  }

  if (activeView === "fuelGovernance") {
    renderFuelGovernance(fuelGovernanceNode, state.data.fuelGovernance, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshAll(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "administration") {
    renderAdministration(administrationNode, null, state.filters, {
      section: state.adminSection,
    });
  }

  if (activeView === "financialMonitoring") {
    renderFinancialMonitoring(financialMonitoringNode, state.data.financialMonitoring, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshFinancialMonitoringOnly(true);
      },
    });
  }

  if (activeView === "financialOperations") {
    renderFinancialOperations(financialOperationsNode, state.data.financialOperations, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshFinancialOperationsOnly(true);
      },
      onRunNow: async () => {
        await runFinancialOperationsNow(state.filters);
        state.cache.clear();
        await refreshFinancialOperationsOnly(true);
      },
    });
  }

  if (activeView === "financialOperationsCenter") {
    renderFinancialOperationsCenter(financialOperationsCenterNode, state.data.financialOperationsCenter, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshFinancialOperationsCenterOnly(true);
      },
    });
  }

  if (activeView === "financialIntelligence") {
    renderFinancialIntelligence(financialIntelligenceNode, state.data.financialIntelligence, state.filters, {
      onRefresh: async () => {
        state.cache.clear();
        await refreshFinancialIntelligenceOnly(true);
      },
      companies: state.companies,
    });
  }

  if (activeView === "stock") {
    renderStock(
      stockNode,
      state.data.stock,
      async (nextPage) => {
        state.pageStock = nextPage;
        writeUrl(state);
        await refreshStockOnly(false);
      },
      {
        filters: state.filters,
        companies: state.companies,
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

async function loadExecutiveWorkspaceBundle(bypassCache = false) {
  ensureDataDefaults();
  await Promise.all([
    loadExecutiveScorecardWithSnapshotFirst(bypassCache),
    loadActionCenterWithSnapshotFirst(bypassCache),
    loadCommercialExecutionWithSnapshotFirst(bypassCache),
    loadCommercialLearningWithSnapshotFirst(bypassCache),
    loadFuelGovernanceWithSnapshotFirst(bypassCache),
    loadNfceIntelligenceWithSnapshotFirst(bypassCache),
    loadNonFuelProductsWithSnapshotFirst(bypassCache),
    loadBenchmarkWithSnapshotFirst(bypassCache),
  ]);
}

function buildWorkspaceDataPayload() {
  return {
    executiveScorecard: state.data.executiveScorecard,
    actionCenter: state.data.actionCenter,
    commercialExecution: state.data.commercialExecution,
    commercialLearning: state.data.commercialLearning,
    fuelGovernance: state.data.fuelGovernance,
    nfceIntelligence: state.data.nfceIntelligence,
    nonFuelProducts: state.data.nonFuelProducts,
    benchmark: state.data.benchmark,
  };
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

async function loadExecutiveCopilotWithSnapshotFirst(bypassCache = false) {
  try {
    const copilot = await fetchExecutiveCopilotCockpit(state.filters);
    state.data.executiveCopilot = {
      cockpit: copilot.cockpit,
      executiveAnswers: copilot.executiveAnswers,
      parecerFinal: copilot.parecerFinal,
      qa: copilot.qa,
      governanceRules: copilot.governanceRules,
      conversationLayer: copilot.conversationLayer,
      recommendationEngine: copilot.recommendationEngine,
      fromSnapshot: copilot.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (copilot.snapshot?.stale) {
      postExecutiveCopilotRefresh(state.filters).catch((error) => {
        console.warn("[executiveCopilot] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[executiveCopilot] falha ao carregar cockpit:", error);
    state.data.executiveCopilot = null;
  }
}

async function loadCashReconciliationWithSnapshotFirst(bypassCache = false) {
  try {
    const [payload, exposure] = await Promise.all([
      fetchCashReconciliationSummary(state.filters),
      fetchCashClosingExposure(state.filters).catch((err) => {
        console.warn("[cashExposure] falha CASH-01:", err);
        return null;
      }),
    ]);
    const data = payload.data || {};
    if (exposure) data.cashExposure = exposure;
    state.data.cashReconciliation = {
      data,
      snapshot: payload.snapshot,
      lastUpdated: new Date().toISOString(),
    };
  } catch (error) {
    console.warn("[cashReconciliation] falha ao carregar conferência:", error);
    state.data.cashReconciliation = null;
  }
}

async function loadOwnerDiretoriaHome(bypassCache = false) {
  try {
    const [payload] = await Promise.all([
      fetchOwnerDiretoriaBundle(state.filters),
      loadExecutiveFollowUp(bypassCache).catch(() => null),
    ]);
    state.data.ownerDiretoriaHome = payload;
  } catch (error) {
    console.warn("[ownerDiretoria] falha ao carregar decisões:", error);
    state.data.ownerDiretoriaHome = null;
  }
}

async function loadExecutiveFollowUp(bypassCache = false) {
  try {
    const payload = await fetchExecutiveFollowUps();
    state.data.executiveFollowUp = payload;
  } catch (error) {
    console.warn("[executiveFollowUp] falha ao carregar acompanhamento:", error);
    state.data.executiveFollowUp = null;
  }
}

async function loadExecutiveFollowUpDetail(requestId, bypassCache = false) {
  if (!requestId) {
    state.data.executiveFollowUpDetail = null;
    return;
  }
  try {
    const payload = await fetchExecutiveFollowUpDetail(requestId);
    state.data.executiveFollowUpDetail = payload;
  } catch (error) {
    console.warn("[executiveFollowUpDetail] falha ao carregar detalhe:", error);
    state.data.executiveFollowUpDetail = null;
  }
}

async function loadFinancialReviewInbox(bypassCache = false) {
  try {
    const payload = await fetchFinancialReviewInbox();
    state.data.financialReviewInbox = payload;
  } catch (error) {
    console.warn("[financialReviewInbox] falha ao carregar conferências:", error);
    state.data.financialReviewInbox = null;
  }
}

async function loadFinancialReviewDetail(requestId, bypassCache = false) {
  if (!requestId) {
    state.data.financialReviewDetail = null;
    return;
  }
  try {
    const payload = await fetchFinancialReviewDetail(requestId);
    state.data.financialReviewDetail = payload;
  } catch (error) {
    console.warn("[financialReviewDetail] falha ao carregar detalhe:", error);
    state.data.financialReviewDetail = null;
  }
}

async function loadDecisionDetail(decisionId, bypassCache = false) {
  if (!decisionId) {
    state.data.decisionDetail = null;
    state.data.decisionReviewRequests = null;
    state.data.decisionExecution = null;
    state.data.executionMetrics = null;
    return;
  }
  try {
    const [payload, reviews] = await Promise.all([
      fetchDecisionEvidence(decisionId),
      fetchDecisionReviewRequests(decisionId),
    ]);
    state.data.decisionDetail = payload;
    state.data.decisionReviewRequests = reviews;
  } catch (error) {
    console.warn("[decisionDetail] falha ao carregar evidências:", error);
    state.data.decisionDetail = null;
    state.data.decisionReviewRequests = null;
  }
  await loadDecisionExecution(decisionId);

  const tenantId = state.data.decisionDetail?.data?.source_metadata?.tenant_id;
  if (tenantId) {
    try {
      const metrics = await fetchExecutionMetricsSummary(tenantId, tenantId);
      state.data.executionMetrics = metrics?.data || null;
    } catch (error) {
      state.data.executionMetrics = null;
    }
  } else {
    state.data.executionMetrics = null;
  }
}

async function loadDecisionExecution(decisionId) {
  if (!decisionId) {
    state.data.decisionExecution = null;
    return;
  }
  try {
    const timeline = await fetchDecisionTimeline(decisionId);
    state.data.decisionExecution = timeline?.data || null;
    decisionExecutionUi.notYetExecuted = false;
  } catch (error) {
    state.data.decisionExecution = null;
    decisionExecutionUi.notYetExecuted = true;
  }
}

async function loadActionCenterWithSnapshotFirst(bypassCache = false) {
  try {
    const ac = await fetchActionCenterCockpit(state.filters);
    state.data.actionCenter = {
      cockpit: ac.cockpit,
      executiveAnswers: ac.executiveAnswers,
      parecerFinal: ac.parecerFinal,
      qa: ac.qa,
      governanceRules: ac.governanceRules,
      fromSnapshot: ac.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (ac.snapshot?.stale) {
      postActionCenterRefresh(state.filters).catch((error) => {
        console.warn("[actionCenter] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[actionCenter] falha ao carregar cockpit:", error);
    state.data.actionCenter = null;
  }
}

async function loadRecommendationsWithSnapshotFirst(bypassCache = false) {
  try {
    const rec = await fetchAutonomousRecommendationsCockpit(state.filters);
    state.data.recommendations = {
      cockpit: rec.cockpit,
      executiveAnswers: rec.executiveAnswers,
      parecerFinal: rec.parecerFinal,
      qa: rec.qa,
      governanceRules: rec.governanceRules,
      executiveFeedEngine: rec.executiveFeedEngine,
      recommendationPrioritizationEngine: rec.recommendationPrioritizationEngine,
      fromSnapshot: rec.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (rec.snapshot?.stale) {
      postAutonomousRecommendationsRefresh(state.filters).catch((error) => {
        console.warn("[recommendations] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[recommendations] falha ao carregar cockpit:", error);
    state.data.recommendations = null;
  }
}

async function loadLearningWithSnapshotFirst(bypassCache = false) {
  try {
    const learning = await fetchClosedLoopLearningCockpit(state.filters);
    state.data.learning = {
      cockpit: learning.cockpit,
      executiveAnswers: learning.executiveAnswers,
      parecerFinal: learning.parecerFinal,
      qa: learning.qa,
      governanceRules: learning.governanceRules,
      executiveFeedbackLoop: learning.executiveFeedbackLoop,
      learningEngine: learning.learningEngine,
      fromSnapshot: learning.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (learning.snapshot?.stale) {
      postClosedLoopLearningRefresh(state.filters).catch((error) => {
        console.warn("[learning] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[learning] falha ao carregar cockpit:", error);
    state.data.learning = null;
  }
}

async function loadNfceIntelligenceWithSnapshotFirst(bypassCache = false) {
  try {
    const nfce = await fetchNfceIntelligenceCockpit(state.filters);
    state.data.nfceIntelligence = {
      cockpit: nfce.cockpit,
      executiveAnswers: nfce.executiveAnswers,
      parecerFinal: nfce.parecerFinal,
      qa: nfce.qa,
      governanceRules: nfce.governanceRules,
      nfceCatalogEngine: nfce.nfceCatalogEngine,
      nfceReconciliationEngine: nfce.nfceReconciliationEngine,
      nfceRiskEngine: nfce.nfceRiskEngine,
      nfceAnomalyEngine: nfce.nfceAnomalyEngine,
      nfceExecutiveIntelligence: nfce.nfceExecutiveIntelligence,
      fromSnapshot: nfce.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (nfce.snapshot?.stale) {
      postNfceIntelligenceRefresh(state.filters).catch((error) => {
        console.warn("[nfceIntelligence] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[nfceIntelligence] falha ao carregar cockpit:", error);
    state.data.nfceIntelligence = null;
  }
}

async function loadLmcIntelligenceWithSnapshotFirst(bypassCache = false) {
  try {
    const lmc = await fetchLmcIntelligenceCockpit(state.filters);
    state.data.lmcIntelligence = {
      cockpit: lmc.cockpit,
      executiveAnswers: lmc.executiveAnswers,
      parecerFinal: lmc.parecerFinal,
      qa: lmc.qa,
      governanceRules: lmc.governanceRules,
      lmcCatalogEngine: lmc.lmcCatalogEngine,
      fuelReconciliationEngine: lmc.fuelReconciliationEngine,
      lossSurplusEngine: lmc.lossSurplusEngine,
      tankIntelligence: lmc.tankIntelligence,
      pumpIntelligence: lmc.pumpIntelligence,
      lmcExecutiveIntelligence: lmc.lmcExecutiveIntelligence,
      fromSnapshot: lmc.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (lmc.snapshot?.stale) {
      postLmcIntelligenceRefresh(state.filters).catch((error) => {
        console.warn("[lmcIntelligence] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[lmcIntelligence] falha ao carregar cockpit:", error);
    state.data.lmcIntelligence = null;
  }
}

async function loadFiscalIntelligenceWithSnapshotFirst(bypassCache = false) {
  try {
    const fiscal = await fetchFiscalIntelligenceCockpit(state.filters);
    state.data.fiscalIntelligence = {
      cockpit: fiscal.cockpit,
      executiveAnswers: fiscal.executiveAnswers,
      parecerFinal: fiscal.parecerFinal,
      qa: fiscal.qa,
      governanceRules: fiscal.governanceRules,
      productFiscalCatalogEngine: fiscal.productFiscalCatalogEngine,
      ncmIntelligenceEngine: fiscal.ncmIntelligenceEngine,
      taxClassificationEngine: fiscal.taxClassificationEngine,
      financialClassificationEngine: fiscal.financialClassificationEngine,
      fiscalRiskEngine: fiscal.fiscalRiskEngine,
      executiveFiscalIntelligence: fiscal.executiveFiscalIntelligence,
      fromSnapshot: fiscal.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (fiscal.snapshot?.stale) {
      postFiscalIntelligenceRefresh(state.filters).catch((error) => {
        console.warn("[fiscalIntelligence] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[fiscalIntelligence] falha ao carregar cockpit:", error);
    state.data.fiscalIntelligence = null;
  }
}

async function loadFiscalReconciliationWithSnapshotFirst(bypassCache = false) {
  try {
    const hub = await fetchFiscalReconciliationCockpit(state.filters);
    state.data.fiscalReconciliation = {
      cockpit: hub.cockpit,
      executiveAnswers: hub.executiveAnswers,
      parecerFinal: hub.parecerFinal,
      qa: hub.qa,
      governanceRules: hub.governanceRules,
      fiscalLineageEngine: hub.fiscalLineageEngine,
      nfceVendaReconciliation: hub.nfceVendaReconciliation,
      productSalesReconciliation: hub.productSalesReconciliation,
      lmcSalesReconciliation: hub.lmcSalesReconciliation,
      fiscalFinancialBridge: hub.fiscalFinancialBridge,
      fiscalRiskConsolidation: hub.fiscalRiskConsolidation,
      fromSnapshot: hub.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (hub.snapshot?.stale) {
      postFiscalReconciliationRefresh(state.filters).catch((error) => {
        console.warn("[fiscalReconciliation] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[fiscalReconciliation] falha ao carregar cockpit:", error);
    state.data.fiscalReconciliation = null;
  }
}

async function loadFuelGovernanceWithSnapshotFirst(bypassCache = false) {
  try {
    const gov = await fetchFuelGovernanceCockpit(state.filters);
    state.data.fuelGovernance = {
      cockpit: gov.cockpit,
      executiveAnswers: gov.executiveAnswers,
      parecerFinal: gov.parecerFinal,
      qa: gov.qa,
      governanceRules: gov.governanceRules,
      lmcComplianceAudit: gov.lmcComplianceAudit,
      routineAdherenceAudit: gov.routineAdherenceAudit,
      operationalDisciplineAudit: gov.operationalDisciplineAudit,
      delayAnalysisEngine: gov.delayAnalysisEngine,
      branchComplianceRanking: gov.branchComplianceRanking,
      fuelGovernanceIntelligence: gov.fuelGovernanceIntelligence,
      processoOperacionalSuficiente: gov.processoOperacionalSuficiente,
      fromSnapshot: gov.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (gov.snapshot?.stale) {
      postFuelGovernanceRefresh(state.filters).catch((error) => {
        console.warn("[fuelGovernance] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[fuelGovernance] falha ao carregar cockpit:", error);
    state.data.fuelGovernance = null;
  }
}

async function loadNonFuelProductsWithSnapshotFirst(bypassCache = false) {
  try {
    const nf = await fetchNonFuelProductsCockpit(state.filters);
    state.data.nonFuelProducts = {
      cockpit: nf.cockpit,
      executiveAnswers: nf.executiveAnswers,
      parecerFinal: nf.parecerFinal,
      qa: nf.qa,
      governanceRules: nf.governanceRules,
      multiTenantScalabilityEngine: nf.multiTenantScalabilityEngine,
      productDepartmentDiscovery: nf.productDepartmentDiscovery,
      productPerformanceBenchmark: nf.productPerformanceBenchmark,
      residualSkuForensics: nf.residualSkuForensics,
      productLookupOptimization: nf.productLookupOptimization,
      departmentRefinement: nf.departmentRefinement,
      multiBranchProductScale: nf.multiBranchProductScale,
      productMasterCoverage: nf.productMasterCoverage,
      productMatchRecovery: nf.productMatchRecovery,
      departmentIntelligence: nf.departmentIntelligence,
      productRevenueIntelligence: nf.productRevenueIntelligence,
      branchProductMix: nf.branchProductMix,
      salesCoverageReconciliation: nf.salesCoverageReconciliation,
      nonFuelSalesEngine: nf.nonFuelSalesEngine,
      productRankingEngine: nf.productRankingEngine,
      branchDepartmentAnalytics: nf.branchDepartmentAnalytics,
      productSalesLineage: nf.productSalesLineage,
      fromSnapshot: nf.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (nf.snapshot?.stale) {
      postNonFuelProductsRefresh(state.filters).catch((error) => {
        console.warn("[nonFuelProducts] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[nonFuelProducts] falha ao carregar cockpit:", error);
    state.data.nonFuelProducts = null;
  }
}

async function loadCommercialExecutionWithSnapshotFirst(bypassCache = false) {
  try {
    const ce = await fetchCommercialExecutionCockpit(state.filters);
    state.data.commercialExecution = {
      cockpit: ce.cockpit,
      executiveAnswers: ce.executiveAnswers,
      parecerFinal: ce.parecerFinal,
      qa: ce.qa,
      governanceRules: ce.governanceRules,
      commercialAssignmentEngine: ce.commercialAssignmentEngine,
      commercialExecutionTracking: ce.commercialExecutionTracking,
      commercialEvidenceEngine: ce.commercialEvidenceEngine,
      commercialOutcomeMeasurement: ce.commercialOutcomeMeasurement,
      revenueLiftTracking: ce.revenueLiftTracking,
      marginImprovementTracking: ce.marginImprovementTracking,
      commercialPerformance: ce.commercialPerformance,
      fromSnapshot: ce.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (ce.snapshot?.stale) {
      postCommercialExecutionRefresh(state.filters).catch((error) => {
        console.warn("[commercialExecution] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[commercialExecution] falha ao carregar cockpit:", error);
    state.data.commercialExecution = null;
  }
}

async function loadCommercialLearningWithSnapshotFirst(bypassCache = false) {
  try {
    const cl = await fetchCommercialLearningCockpit(state.filters);
    state.data.commercialLearning = {
      cockpit: cl.cockpit,
      executiveAnswers: cl.executiveAnswers,
      parecerFinal: cl.parecerFinal,
      qa: cl.qa,
      governanceRules: cl.governanceRules,
      recommendationEffectivenessEngine: cl.recommendationEffectivenessEngine,
      responsiblePerformanceEngine: cl.responsiblePerformanceEngine,
      branchLearningEngine: cl.branchLearningEngine,
      recommendationCalibrationEngine: cl.recommendationCalibrationEngine,
      outcomeLearningEngine: cl.outcomeLearningEngine,
      executiveLearningReport: cl.executiveLearningReport,
      fromSnapshot: cl.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (cl.snapshot?.stale) {
      postCommercialLearningRefresh(state.filters).catch((error) => {
        console.warn("[commercialLearning] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[commercialLearning] falha ao carregar cockpit:", error);
    state.data.commercialLearning = null;
  }
}

async function loadCommercialCopilotWithSnapshotFirst(bypassCache = false) {
  try {
    const cc = await fetchCommercialCopilotCockpit(state.filters);
    state.data.commercialCopilot = {
      cockpit: cc.cockpit,
      executiveAnswers: cc.executiveAnswers,
      parecerFinal: cc.parecerFinal,
      qa: cc.qa,
      governanceRules: cc.governanceRules,
      commercialKnowledgeEngine: cc.commercialKnowledgeEngine,
      commercialReasoningEngine: cc.commercialReasoningEngine,
      commercialRecommendationEngine: cc.commercialRecommendationEngine,
      commercialActionCenterIntegration: cc.commercialActionCenterIntegration,
      commercialConversationLayer: cc.commercialConversationLayer,
      commercialGovernanceLayer: cc.commercialGovernanceLayer,
      fromSnapshot: cc.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (cc.snapshot?.stale) {
      postCommercialCopilotRefresh(state.filters).catch((error) => {
        console.warn("[commercialCopilot] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[commercialCopilot] falha ao carregar cockpit:", error);
    state.data.commercialCopilot = null;
  }
}

async function loadExecutiveDecisionWithSnapshotFirst(bypassCache = false) {
  try {
    const decision = await fetchExecutiveDecisionCockpit(state.filters);
    state.data.executiveDecision = {
      cockpit: decision.cockpit,
      executiveAnswers: decision.executiveAnswers,
      parecerFinal: decision.parecerFinal,
      decisaoArquitetural: decision.decisaoArquitetural,
      qa: decision.qa,
      planoCorporativoConsolidado: decision.planoCorporativoConsolidado,
      fromSnapshot: decision.snapshot?.hit,
      lastUpdated: new Date().toISOString(),
    };
    if (decision.snapshot?.stale) {
      postExecutiveDecisionRefresh(state.filters).catch((error) => {
        console.warn("[executiveDecision] refresh em background falhou:", error);
      });
    }
  } catch (error) {
    console.warn("[executiveDecision] falha ao carregar cockpit:", error);
    state.data.executiveDecision = null;
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
      ...normalizeCashFlow(snapshot.flow),
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
  state.data.cashFlow = flow?.unavailable
    ? flow
    : {
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
    try {
      state.data.financeCenter.directorReconciliation = await (
        bypassCache
          ? postDirectorFinancialReconciliationRefresh(state.filters)
          : fetchDirectorFinancialReconciliation(state.filters)
      );
    } catch (error) {
      state.data.financeCenter.directorReconciliation = {
        complete: false,
        warnings: ["Conciliação da Diretoria indisponível; totais bloqueados."],
        executiveSummary: [],
      };
    }
    if (state.data.financeCenter.directorReconciliation?.publication?.dreTotalsReleased) {
      try {
        state.data.financeCenter.completeDepartmentalDre = await fetchCompleteDepartmentalDre(state.filters);
      } catch (error) {
        state.data.financeCenter.completeDepartmentalDre = null;
      }
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
  try {
    state.data.financeCenter.directorReconciliation = await (
      bypassCache
        ? postDirectorFinancialReconciliationRefresh(state.filters)
        : fetchDirectorFinancialReconciliation(state.filters)
    );
  } catch (error) {
    state.data.financeCenter.directorReconciliation = {
      complete: false,
      warnings: ["Conciliação da Diretoria indisponível; totais bloqueados."],
      executiveSummary: [],
    };
  }
  if (state.data.financeCenter.directorReconciliation?.publication?.dreTotalsReleased) {
    try {
      state.data.financeCenter.completeDepartmentalDre = await fetchCompleteDepartmentalDre(state.filters);
    } catch (error) {
      state.data.financeCenter.completeDepartmentalDre = null;
    }
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
    state.data.fuelExecutive = normalizeFuelExecutive(
      enrichFuelExecutive(state.productCatalog, snapshot.fuel.data)
    );
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
  if (!state.data.fuelExecutive?.unavailable) {
    state.data.fuelExecutive = normalizeFuelExecutive(
      enrichFuelExecutive(state.productCatalog, state.data.fuelExecutive)
    );
  }
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
        { ...state.filters, page: 1, limit: 500 },
        () => fetchFinancialExpenses(state.filters, 1, 500),
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

    state.data.overview = overview?.data ?? overview;
    state.data.overviewResilience = overview?.resilience ?? null;
    state.data.expenses = expenses?.data ?? expenses;
    state.data.expensesResilience = expenses?.resilience ?? null;
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

function previousPeriodFilters(filters) {
  const start = new Date(`${filters.dataInicial}T00:00:00`);
  const endDate = new Date(`${filters.dataFinal}T00:00:00`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(endDate.getTime())) return null;
  const days = Math.max(1, Math.round((endDate - start) / 86400000) + 1);
  const previousEnd = new Date(start);
  previousEnd.setDate(previousEnd.getDate() - 1);
  const previousStart = new Date(previousEnd);
  previousStart.setDate(previousStart.getDate() - days + 1);
  return {
    ...filters,
    dataInicial: toLocalIsoDate(previousStart),
    dataFinal: toLocalIsoDate(previousEnd),
  };
}

async function safeLoad(loader) {
  try {
    return await loader();
  } catch (error) {
    console.warn("[president] bloco indisponivel:", error);
    return null;
  }
}

async function loadPresidentDashboard(bypassCache = false) {
  const snapshotBundle = await fetchPresidentSnapshotBundle(state.filters);
  if (snapshotBundle.hit) {
    const snapshotData = {
      overview: snapshotBundle.overview?.data ?? snapshotBundle.overview,
      expenses: snapshotBundle.expenses?.data ?? snapshotBundle.expenses,
      sales: snapshotBundle.sales?.data ?? snapshotBundle.sales,
      stock: snapshotBundle.stock?.data ?? snapshotBundle.stock,
      scorecard: snapshotBundle.scorecard?.data ?? snapshotBundle.scorecard,
      fuelGovernance: snapshotBundle.fuelGovernance?.data ?? snapshotBundle.fuelGovernance,
      products: snapshotBundle.products?.data ?? snapshotBundle.products,
      snapshotHit: true,
    };

    // Mostra os números disponíveis sem bloquear a tela pela conciliação.
    state.data.presidentDashboard = buildPresidentDashboardData(snapshotData);
    renderAll();
    setLoading(false);

    const directorReconciliation = await safeLoad(() => fetchDirectorFinancialReconciliation(state.filters));
    const completeDre = directorReconciliation?.publication?.dreTotalsReleased
      ? await safeLoad(() => fetchCompleteDepartmentalDre(state.filters))
      : null;
    state.data.presidentDashboard = buildPresidentDashboardData({
      ...snapshotData,
      directorReconciliation,
      completeDre,
    });
    return;
  }

  const previousFilters = previousPeriodFilters(state.filters);
  const [
    kpis,
    previousKpis,
    overview,
    previousOverview,
    expenses,
    sales,
    stock,
    fuelSummary,
    scorecard,
    directorReconciliation,
  ] = await Promise.all([
    safeLoad(() => getCached("president_kpis", state.filters, () => fetchKpis(state.filters), bypassCache)),
    previousFilters
      ? safeLoad(() => getCached("president_previous_kpis", previousFilters, () => fetchKpis(previousFilters), bypassCache))
      : null,
    safeLoad(() => getCached("president_overview", state.filters, () => fetchFinancialOverview(state.filters), bypassCache)),
    previousFilters
      ? safeLoad(() => getCached("president_previous_overview", previousFilters, () => fetchFinancialOverview(previousFilters), bypassCache))
      : null,
    safeLoad(() =>
      getCached(
        "president_expenses",
        { ...state.filters, page: 1, limit: 500 },
        () => fetchFinancialExpenses(state.filters, 1, 500),
        bypassCache
      )
    ),
    safeLoad(() =>
      getCached(
        "president_sales",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchSales, state.filters, state.limitSales),
        bypassCache
      )
    ),
    safeLoad(() =>
      getCached(
        "president_stock",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchStock, state.filters, state.limitStock),
        bypassCache
      )
    ),
    safeLoad(() => getCached("president_fuel_summary", state.filters, () => fetchFuelSummary(state.filters), bypassCache)),
    safeLoad(() =>
      getCached("president_scorecard", state.filters, () => fetchExecutiveScorecardCockpit(state.filters), bypassCache)
    ),
    safeLoad(() => fetchDirectorFinancialReconciliation(state.filters)),
  ]);

  const completeDre = directorReconciliation?.publication?.dreTotalsReleased
    ? await safeLoad(() => fetchCompleteDepartmentalDre(state.filters))
    : null;

  state.data.presidentDashboard = buildPresidentDashboardData({
    kpis,
    previousKpis,
    overview: overview?.data ?? overview,
    previousOverview: previousOverview?.data ?? previousOverview,
    expenses: expenses?.data ?? expenses,
    sales,
    stock,
    fuelSummary: enrichFuelSummary(
      state.productCatalog,
      Array.isArray(fuelSummary) ? fuelSummary : Array.isArray(fuelSummary?.data) ? fuelSummary.data : []
    ),
    scorecard: scorecard?.data ?? scorecard,
    directorReconciliation,
    completeDre,
  });
}

async function refreshAll(bypassCache = false) {
  if (state.view === "administration") {
    setError("");
    setLoading(true);
    try {
      renderAll();
    } finally {
      setLoading(false);
    }
    return;
  }

  if (state.view === "presidentDashboard") {
    setError("");
    setLoading(true);
    try {
      await refreshCompanies(bypassCache);
      await loadPresidentDashboard(bypassCache);
      renderAll();
    } catch (error) {
      setError(error.message || String(error));
    } finally {
      setLoading(false);
    }
    return;
  }

  if (state.view === "executiveWorkspace") {
    setError("");
    setLoading(true);
    try {
      await refreshCompanies(bypassCache);
      await loadExecutiveWorkspaceBundle(bypassCache);
      renderAll();
    } catch (error) {
      setError(error.message || String(error));
    } finally {
      setLoading(false);
    }
    return;
  }

  if (state.view === "executive") {
    setView("executiveWorkspace");
    await refreshAll(bypassCache);
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

    if (state.view === "financialHub") {
      const overviewResult = await getCached("overview", state.filters, () => fetchFinancialOverview(state.filters), bypassCache);
      state.data.overview = overviewResult?.data ?? overviewResult;
      state.data.overviewResilience = overviewResult?.resilience ?? null;
      const hubTab = state.hubTab || "receitas";
      if (hubTab === "receitas") {
        state.data.revenueTotal = await loadRevenueTotal(state.filters, bypassCache);
      } else {
        state.data.revenueTotal = null;
      }
      const expensesResult = await getCached(
        "expenses",
        { ...state.filters, page: state.pageExpenses, limit: state.limitExpenses },
        () => fetchFinancialExpenses(state.filters, state.pageExpenses, state.limitExpenses),
        bypassCache
      );
      state.data.expenses = expensesResult?.data ?? expensesResult;
      state.data.expensesResilience = expensesResult?.resilience ?? null;
    }

    if (state.view === "dashboard") {
      const overviewResult = await getCached("overview", state.filters, () => fetchFinancialOverview(state.filters), bypassCache);
      state.data.overview = overviewResult?.data ?? overviewResult;
      state.data.overviewResilience = overviewResult?.resilience ?? null;
      state.data.revenueTotal = await loadRevenueTotal(state.filters, bypassCache);
    }

    if (state.view === "expenses") {
      const expensesResult = await getCached(
        "expenses",
        { ...state.filters, page: state.pageExpenses, limit: state.limitExpenses },
        () => fetchFinancialExpenses(state.filters, state.pageExpenses, state.limitExpenses),
        bypassCache
      );
      state.data.expenses = expensesResult?.data ?? expensesResult;
      state.data.expensesResilience = expensesResult?.resilience ?? null;
    }

    if (state.view === "treasuryHub") {
      const tab = state.hubTab || "fluxo";
      if (tab === "contas") {
        state.data.accounts = await getCached(
          "accounts",
          { ...state.filters, scope: "all" },
          () => fetchDatasetAcrossCompanies(fetchAccountsPayable, state.filters, state.limitAccounts),
          bypassCache
        );
      } else if (tab === "extratos") {
        await loadCashOperationsWithSnapshotFirst(bypassCache);
      } else if (tab === "conciliacao") {
        await loadFinanceCenterWithSnapshotFirst(bypassCache);
      } else {
        await loadCashFlowWithSnapshotFirst(bypassCache);
      }
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
      try {
        state.data.sales = await getCached(
          "sales",
          { ...state.filters, scope: "all" },
          () => fetchDatasetAcrossCompanies(fetchSales, state.filters, state.limitSales),
          bypassCache
        );
      } catch (error) {
        console.warn("[sales] falha ao carregar vendas:", error);
        state.data.sales = { data: [], page: 1, limit: state.limitSales, total: 0 };
      }
      try {
        state.data.fuelSummary = await getCached(
          "fuelSummary",
          state.filters,
          () => fetchFuelSummary(state.filters),
          bypassCache
        );
        state.data.fuelSummary = enrichFuelSummary(state.productCatalog, state.data.fuelSummary || []);
      } catch (error) {
        console.warn("[sales] falha ao carregar resumo de combustíveis:", error);
        state.data.fuelSummary = [];
      }
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

    if (state.view === "executiveDecision") {
      await loadExecutiveDecisionWithSnapshotFirst(bypassCache);
    }

    if (state.view === "actionCenter") {
      await loadActionCenterWithSnapshotFirst(bypassCache);
    }

    if (state.view === "cashReconciliation") {
      await loadCashReconciliationWithSnapshotFirst(bypassCache);
    }

    if (state.view === "ownerDiretoriaHome") {
      await loadOwnerDiretoriaHome(bypassCache);
    }

    if (state.view === "executiveFollowUp") {
      await loadExecutiveFollowUp(bypassCache);
    }

    if (state.view === "executiveFollowUpDetail" && state.followUpRequestId) {
      await loadExecutiveFollowUpDetail(state.followUpRequestId, bypassCache);
    }

    if (state.view === "financialReviewInbox") {
      await loadFinancialReviewInbox(bypassCache);
    }

    if (state.view === "financialReviewDetail" && state.financialReviewRequestId) {
      await loadFinancialReviewDetail(state.financialReviewRequestId, bypassCache);
    }

    if (state.view === "decisionDetail" && state.decisionId) {
      await loadDecisionDetail(state.decisionId, bypassCache);
    }

    if (state.view === "executiveCopilot") {
      await loadExecutiveCopilotWithSnapshotFirst(bypassCache);
    }

    if (state.view === "recommendations") {
      await loadRecommendationsWithSnapshotFirst(bypassCache);
    }

    if (state.view === "learning") {
      await loadLearningWithSnapshotFirst(bypassCache);
    }

    if (state.view === "nfceIntelligence") {
      await loadNfceIntelligenceWithSnapshotFirst(bypassCache);
    }

    if (state.view === "lmcIntelligence") {
      await loadLmcIntelligenceWithSnapshotFirst(bypassCache);
    }

    if (state.view === "fiscalIntelligence") {
      await loadFiscalIntelligenceWithSnapshotFirst(bypassCache);
    }

    if (state.view === "fiscalReconciliation") {
      await loadFiscalReconciliationWithSnapshotFirst(bypassCache);
    }

    if (state.view === "fuelGovernance") {
      await loadFuelGovernanceWithSnapshotFirst(bypassCache);
    }

    if (state.view === "productsHub") {
      const tab = state.hubTab || "mix";
      if (tab === "oportunidades") {
        await loadCommercialCopilotWithSnapshotFirst(bypassCache);
      } else if (tab === "performance") {
        await loadCommercialLearningWithSnapshotFirst(bypassCache);
      } else {
        await loadNonFuelProductsWithSnapshotFirst(bypassCache);
      }
    }

    if (state.view === "nonFuelProducts") {
      await loadNonFuelProductsWithSnapshotFirst(bypassCache);
    }

    if (state.view === "commercialExecution") {
      await loadCommercialExecutionWithSnapshotFirst(bypassCache);
    }

    if (state.view === "commercialLearning") {
      await loadCommercialLearningWithSnapshotFirst(bypassCache);
    }

    if (state.view === "commercialCopilot") {
      await loadCommercialCopilotWithSnapshotFirst(bypassCache);
    }

    if (state.view === "financialMonitoring") {
      await refreshFinancialOperationsCenterOnly(bypassCache);
    }

    if (state.view === "financialOperations") {
      await refreshFinancialOperationsCenterOnly(bypassCache);
    }

    if (state.view === "financialOperationsCenter") {
      await refreshFinancialOperationsCenterOnly(bypassCache);
    }

    if (state.view === "financialIntelligence") {
      await refreshFinancialIntelligenceOnly(bypassCache);
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

async function refreshFinancialMonitoringOnly(bypassCache = false) {
  const raw = await getCached(
    "financialMonitoring",
    state.filters,
    () => fetchFinancialSnapshotHealthCockpit(state.filters),
    bypassCache
  );
  state.data.financialMonitoring = raw?.data ? raw : { data: raw?.data ?? raw };
  renderAll();
}

async function refreshFinancialIntelligenceOnly(bypassCache = false) {
  const raw = await getCached(
    "financialIntelligence",
    state.filters,
    () => fetchFinancialIntelligenceCockpit(state.filters),
    bypassCache
  );
  state.data.financialIntelligence = raw?.data ? raw : { data: raw?.data ?? raw };
  renderAll();
}

async function refreshFinancialOperationsCenterOnly(bypassCache = false) {
  const raw = await getCached(
    "financialOperationsCenter",
    state.filters,
    () => fetchFinancialOperationsCenterCockpit(state.filters),
    bypassCache
  );
  state.data.financialOperationsCenter = raw?.data ? raw : { data: raw?.data ?? raw };
  renderAll();
}

async function refreshFinancialOperationsOnly(bypassCache = false) {
  const raw = await getCached(
    "financialOperations",
    state.filters,
    () => fetchFinancialOperationsStatus(state.filters),
    bypassCache
  );
  state.data.financialOperations = raw?.data ? raw : { data: raw?.data ?? raw };
  renderAll();
}

async function refreshExpensesOnly(bypassCache = false) {
  setError("");
  setLoading(true);
  try {
    const expensesResult = await getCached(
      "expenses",
      { ...state.filters, page: state.pageExpenses, limit: state.limitExpenses },
      () => fetchFinancialExpenses(state.filters, state.pageExpenses, state.limitExpenses),
      bypassCache
    );
    state.data.expenses = expensesResult?.data ?? expensesResult;
    state.data.expensesResilience = expensesResult?.resilience ?? null;
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
    try {
      state.data.sales = await getCached(
        "sales",
        { ...state.filters, scope: "all" },
        () => fetchDatasetAcrossCompanies(fetchSales, state.filters, state.limitSales),
        bypassCache
      );
    } catch (error) {
      console.warn("[sales] falha ao carregar vendas:", error);
      state.data.sales = { data: [], page: 1, limit: state.limitSales, total: 0 };
    }
    try {
      state.data.fuelSummary = await getCached(
        "fuelSummary",
        state.filters,
        () => fetchFuelSummary(state.filters),
        bypassCache
      );
      state.data.fuelSummary = enrichFuelSummary(state.productCatalog, state.data.fuelSummary || []);
    } catch (error) {
      console.warn("[sales] falha ao carregar resumo de combustíveis:", error);
      state.data.fuelSummary = [];
    }

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

function markAppReady() {
  window.__LOGOS_APP_READY = true;
  document.querySelector("#bootStatus")?.remove();
}

try {
  mountFilters();

  document.querySelector("#refreshBtn")?.addEventListener("click", async () => {
    state.cache.clear();
    await refreshAll(true);
  });

  setView(state.view);
  writeUrl(state);
  refreshAll(false);
  markAppReady();
} catch (error) {
  const bootStatus = document.querySelector("#bootStatus");
  if (bootStatus) {
    bootStatus.className = "state error";
    bootStatus.textContent = `Falha ao iniciar a interface: ${error?.message || error}`;
  } else {
    throw error;
  }
}
