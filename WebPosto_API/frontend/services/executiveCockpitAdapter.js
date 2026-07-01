/**
 * RT-06 — Adaptador universal cockpit executivo.
 * Converte payload cockpit + executiveAnswers em 1ª dobra padronizada.
 * Zero API nova — só reorganização UX.
 */
import { getNomeFilial } from "../components/filiais.js";
import {
  bindExecutiveNav,
  renderExecutiveFirstFold,
  wrapExecutiveDetail,
} from "../components/executiveFirstFold.js";
import { renderExecutiveInsightDetail } from "../components/executiveInsightDetail.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "./executiveBrief.js";
import { buildChartBars, countKpi, moneyKpi, periodSubtitle } from "./executiveKpis.js";
import { formatCurrency } from "./formatters.js";
import { downloadCsv } from "./export.js";

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function firstDefined(...values) {
  for (const v of values) {
    if (v != null && v !== "" && v !== "—") return v;
  }
  return null;
}

function pickArray(payload, cockpit, keys) {
  for (const key of keys) {
    const fromPayload = key.split(".").reduce((acc, k) => acc?.[k], payload);
    if (Array.isArray(fromPayload) && fromPayload.length) return fromPayload;
    if (Array.isArray(cockpit?.[key]) && cockpit[key].length) return cockpit[key];
  }
  return [];
}

function buildStandardKpis(exec, cockpit, overrides = []) {
  if (overrides?.length >= 4) return overrides.slice(0, 4);
  const receita = firstDefined(
    exec["1_receitaProdutosVendidos"],
    exec["1_faturamento"],
    exec["6_receitaRealizada"],
    cockpit.receitaTotal,
    cockpit.receitaRealizada,
    cockpit.faturamento
  );
  const despesa = firstDefined(exec["2_despesas"], cockpit.totalDespesas, cockpit.despesas);
  const margem = firstDefined(
    exec["9_margemRealizada"],
    cockpit.margemRealizada,
    cockpit.margemBruta,
    exec["4_margem"]
  );
  const alertas = firstDefined(
    exec["1_totalAcoes"],
    (cockpit.prioridade1 || []).length,
    (cockpit.semEvidencia || []).length,
    exec["6_riscosFiscais"],
    0
  );
  return [
    { label: "Receita", value: moneyKpi(receita) !== "Dados indisponíveis" ? moneyKpi(receita) : countKpi(receita), trendPct: null, status: "ok" },
    { label: "Despesa", value: moneyKpi(despesa) !== "Dados indisponíveis" ? moneyKpi(despesa) : countKpi(despesa), trendPct: null, status: "warn" },
    { label: "Margem", value: moneyKpi(margem) !== "Dados indisponíveis" ? moneyKpi(margem) : countKpi(margem), trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: String(alertas ?? 0),
      trendPct: null,
      status: Number(alertas) > 0 ? "crit" : "ok",
    },
  ];
}

function autoChart(payload, cockpit) {
  const sources = [
    pickArray(payload, cockpit, ["rankingFiliais"]),
    payload.branchComplianceRanking?.ranking,
    payload.commercialPerformance?.porFilial,
    payload.nfceRiskEngine?.risks,
    payload.fiscalRiskEngine?.risks,
    cockpit.prioridade1,
    cockpit.planoAcao,
    cockpit.topOcorrencias,
    cockpit.pareto8020,
    payload.productRevenueIntelligence?.pareto,
  ].find((a) => Array.isArray(a) && a.length);

  if (!sources) return { bars: [], title: "Indicadores do período" };

  const bars = buildChartBars(sources, {
    labelKey: sources[0]?.nome ? "nome" : sources[0]?.empresaCodigo ? "empresaCodigo" : sources[0]?.label ? "label" : "tipo",
    valueKey: sources[0]?.valor != null ? "valor" : sources[0]?.conformidadePct != null ? "conformidadePct" : sources[0]?.quantidade != null ? "quantidade" : "total",
    max: 7,
  });
  return { bars, title: "Distribuição no período" };
}

function autoBrief(title, exec, cockpit, payload) {
  const execVals = Object.entries(exec || {}).filter(([, v]) => v != null && v !== "");
  const what = execVals[0]
    ? `${title}: ${String(execVals[0][1]).slice(0, 80)}`
    : `${title} consolidado no período selecionado.`;

  const delays = payload?.delayAnalysisEngine?.atrasos || cockpit?.atrasos || [];
  const semEvidencia = (cockpit?.semEvidencia || []).length;
  const why =
    delays.length > 0
      ? `${delays.length} lacuna(s) operacional(is) identificada(s).`
      : semEvidencia > 0
        ? `${semEvidencia} ação(ões) sem evidência de execução.`
        : execVals[1]
          ? `Driver: ${String(execVals[1][1]).slice(0, 80)}`
          : "Operação dentro do padrão esperado.";

  const filiais = pickArray(payload, cockpit, ["rankingFiliais"]) || payload.commercialPerformance?.porFilial || [];
  const worst = filiais.length
    ? [...filiais].sort((a, b) => num(a.conformidadePct ?? a.score ?? 100) - num(b.conformidadePct ?? b.score ?? 100))[0]
    : null;
  const where = worst
    ? `Filial ${getNomeFilial(worst.empresaCodigo ?? worst.codigo)}`
    : delays[0]
      ? `Filial ${getNomeFilial(delays[0].empresaCodigo)}`
      : "Rede consolidada";

  const p1 = (cockpit?.prioridade1 || [])[0];
  const actionNow = p1
    ? `Executar: ${p1.acao || p1.titulo || p1.tipo || "ação prioritária"}`
    : delays[0]
      ? `Regularizar LMC/atraso na filial ${getNomeFilial(delays[0].empresaCodigo)}`
      : "Manter rotina e monitorar indicadores.";

  return buildFourQuestionBrief({ what, why, where, actionNow });
}

function autoAlerts(payload, cockpit, defaultView = "") {
  const items = [];
  (cockpit.prioridade1 || []).slice(0, 2).forEach((row) => {
    items.push(
      enrichAlert(
        {
          severity: "ALTO",
          title: row.acao || row.titulo || row.tipo || "Ação prioritária",
          detail: row.ownerName || "",
          view: defaultView,
          origin: "Operação",
        },
        { why: row.lifecycleStatus || "Prioridade 1", where: row.empresaCodigo ? `Filial ${row.empresaCodigo}` : "Rede", actionNow: "Executar hoje" }
      )
    );
  });
  (payload?.delayAnalysisEngine?.atrasos || cockpit.atrasos || []).slice(0, 2).forEach((row) => {
    items.push(
      enrichAlert(
        {
          severity: "ALTO",
          title: `Atraso LMC — ${getNomeFilial(row.empresaCodigo)}`,
          detail: `${row.atrasoDias ?? row.diasAtraso ?? "—"} dia(s)`,
          view: "fuelGovernance",
          origin: "Combustível",
        },
        { why: row.tipo || "Lacuna operacional", where: getNomeFilial(row.empresaCodigo), actionNow: "Completar LMC" }
      )
    );
  });
  (cockpit.semEvidencia || []).slice(0, 1).forEach(() => {
    items.push(
      enrichAlert(
        { severity: "MÉDIO", title: "Ações sem evidência", detail: `${cockpit.semEvidencia.length} pendente(s)`, view: "actionCenter", origin: "Financeiro" },
        { why: "Falta comprovação de execução", where: "Rede", actionNow: "Anexar evidências" }
      )
    );
  });
  return items.slice(0, 3);
}

function autoBranches(payload, cockpit, defaultView = "") {
  const filiais =
    payload.branchComplianceRanking?.ranking ||
    payload.commercialPerformance?.porFilial ||
    cockpit.rankingFiliais ||
    [];
  return mapCriticalBranches(
    [...filiais]
      .sort((a, b) => num(a.conformidadePct ?? a.score ?? 100) - num(b.conformidadePct ?? b.score ?? 100))
      .slice(0, 3)
      .map((row) => ({
        name: getNomeFilial(row.empresaCodigo ?? row.codigo),
        metric: row.conformidadePct != null ? `${row.conformidadePct}%` : row.receita != null ? formatCurrency(row.receita) : row.risco || "—",
        tag: "Crítica",
        view: defaultView,
      }))
  );
}

function autoActions(cockpit, defaultView = "") {
  const rows = [...(cockpit.prioridade1 || []), ...(cockpit.planoAcao || []), ...(cockpit.vencidas || [])];
  return mapPriorityActions(
    rows.slice(0, 3).map((row) => ({
      title: row.acao || row.titulo || row.tipo || row.actionId || "Ação",
      detail: row.ownerName || row.responsavelNome || "",
      view: defaultView,
    }))
  );
}

function autoRisks(payload, cockpit) {
  const risks =
    payload.nfceRiskEngine?.risks ||
    payload.fiscalRiskEngine?.risks ||
    payload.fiscalRiskConsolidation?.risks ||
    cockpit.topRiscos ||
    [];
  return mapRisks(
    risks.slice(0, 3).map((r) => ({
      title: r.title || r.tipo || r.nome || getNomeFilial(r.empresaCodigo) || "Risco",
      detail: r.descricao || r.message || "",
      severity: r.risco || r.level || r.severidade || "ALTO",
    }))
  );
}

function autoOpportunities(cockpit, payload, defaultView = "") {
  const opps = cockpit.recomendacoes || payload.recommendations || cockpit.planoAcao || [];
  return mapOpportunities(
    opps.slice(0, 3).map((row) => ({
      title: row.recomendacao || row.titulo || row.tipo || "Oportunidade",
      impact: row.impactoEstimado != null ? formatCurrency(row.impactoEstimado) : row.roiEsperado != null ? formatCurrency(row.roiEsperado) : "",
      view: defaultView,
    }))
  );
}

/**
 * Renderiza página cockpit com 1ª dobra executiva + detalhamento recolhido.
 */
export function renderExecutiveCockpitPage(node, payload, filters, config = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando ${config.title || "…"}</p>`;
    return;
  }

  const cockpit = payload.cockpit || payload.data?.cockpit || {};
  const exec = payload.executiveAnswers || payload.data?.executiveAnswers || {};
  const { bars, title: chartTitle } = autoChart(payload, cockpit);

  const brief = config.brief || autoBrief(config.title, exec, cockpit, payload);
  const criticalBranches = config.criticalBranches ?? autoBranches(payload, cockpit, config.defaultView);
  const priorityActions = config.priorityActions ?? autoActions(cockpit, config.defaultView);
  const risks = config.risks ?? autoRisks(payload, cockpit);
  const opportunities = config.opportunities ?? autoOpportunities(cockpit, payload, config.defaultView);
  const alerts = config.alerts ?? autoAlerts(payload, cockpit, config.defaultView);

  const firstFold = renderExecutiveFirstFold({
    title: config.title || "Visão Executiva",
    actionsHtml: "",
    kpis: config.kpis || buildStandardKpis(exec, cockpit, config.kpiOverrides),
    chartBars: config.chartBars || bars,
    chartTitle: config.chartTitle || chartTitle,
    alerts,
  });

  const detailBody =
    typeof config.detailBuilder === "function"
      ? config.detailBuilder(cockpit, payload, exec)
      : config.detailHtml || "";

  const insight = renderExecutiveInsightDetail({
    brief,
    criticalBranches,
    priorityActions,
    risks,
    opportunities,
  });

  node.innerHTML = `${firstFold}${wrapExecutiveDetail(`${insight}${detailBody}`, config.detailSummary || "Detalhamento")}`;

  bindExecutiveNav(node, config.onNavigate);

  if (config.refreshButtonId) {
    node.querySelector(`#${config.refreshButtonId}`)?.addEventListener("click", () => config.onRefresh?.());
  }
  if (config.exportButtonId && config.exportData) {
    node.querySelector(`#${config.exportButtonId}`)?.addEventListener("click", () => {
      downloadCsv(config.exportFileName || "export.csv", config.exportData);
    });
  }
}

/**
 * Páginas baseadas em tabela (vendas, estoque, contas).
 */
export function renderExecutiveTablePage(node, payload, filters, config = {}) {
  if (!node) return;
  const rows = payload?.data || [];
  if (!rows.length && !payload) {
    node.innerHTML = `<p class="muted">Carregando ${config.title || "…"}</p>`;
    return;
  }

  const valueKey = config.valueKey || "valor";
  const total = rows.reduce((acc, row) => acc + Number(row[valueKey] || row.quantidade || 0), 0);
  const filialKey = config.filialAccessor || ((row) => row.filial || row.empresaCodigo || "—");
  const byFilial = {};
  rows.forEach((row) => {
    const name = typeof filialKey === "function" ? filialKey(row) : row[filialKey];
    if (!name) return;
    byFilial[name] = (byFilial[name] || 0) + Number(row[valueKey] || row.quantidade || 0);
  });
  const topFilial = Object.entries(byFilial).sort((a, b) => b[1] - a[1])[0];

  const brief = buildFourQuestionBrief({
    what: `${config.title}: ${config.formatTotal ? config.formatTotal(total) : total} no período.`,
    why: topFilial ? `${topFilial[0]} concentra o maior volume.` : "Distribuição equilibrada.",
    where: topFilial ? topFilial[0] : "Rede",
    actionNow: topFilial ? `Revisar ${topFilial[0]} hoje.` : "Manter monitoramento.",
  });

  const chartBars = buildChartBars(
    Object.entries(byFilial)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 7)
      .map(([label, valor]) => ({ label, valor })),
    { labelKey: "label", valueKey: "valor", max: 7 }
  );

  const firstFold = renderExecutiveFirstFold({
    title: config.title,
    actionsHtml: "",
    kpis: config.kpis || [
      { label: "Receita", value: config.formatTotal ? config.formatTotal(total) : String(total), trendPct: null, status: "ok" },
      { label: "Despesa", value: "Dados indisponíveis", trendPct: null, status: "ok" },
      { label: "Margem", value: "Dados indisponíveis", trendPct: null, status: "ok" },
      { label: "Alertas", value: String(Object.keys(byFilial).length), trendPct: null, status: "ok" },
    ],
    chartBars,
    chartTitle: config.chartTitle || "Volume por filial",
    alerts: topFilial
      ? [
          enrichAlert(
            { severity: "MÉDIO", title: `Maior volume — ${topFilial[0]}`, detail: config.formatTotal ? config.formatTotal(topFilial[1]) : String(topFilial[1]), view: config.defaultView || "", origin: config.title },
            { why: "Concentração acima da média", where: topFilial[0], actionNow: "Analisar detalhamento" }
          ),
        ]
      : [],
  });

  const insight = renderExecutiveInsightDetail({
    brief,
    criticalBranches: mapCriticalBranches(
      Object.entries(byFilial)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([name, val]) => ({
          name,
          metric: config.formatTotal ? config.formatTotal(val) : String(val),
          tag: config.branchTag || "Volume",
          view: config.defaultView || "",
        }))
    ),
  });

  const detail =
    typeof config.detailBuilder === "function" ? config.detailBuilder(rows, payload) : config.detailHtml || "";

  node.innerHTML = `${firstFold}${wrapExecutiveDetail(`${insight}${detail}`, config.detailSummary || "Detalhamento")}`;
  bindExecutiveNav(node, config.onNavigate);
}

export { buildStandardKpis, autoBrief, autoChart, autoAlerts };
