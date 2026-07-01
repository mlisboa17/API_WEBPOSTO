import { renderOverviewCards } from "../components/cards.js";
import { renderTable } from "../components/table.js";
import { formatCurrency } from "../services/format.js";
import { formatMissing } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";
import { bindExecutiveNav } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

export function renderDashboard(container, overview, options = {}) {
  const posts = overview?.postos || [];
  const consolidado = overview?.consolidado || {};
  const filters = options.filters || {};

  const despesa = Number(consolidado.total_despesas || 0);
  const aPagar = Number(consolidado.total_a_pagar || 0);
  const receitaInformada = options.revenueTotal ?? options.receivablesTotal;
  const receita =
    receitaInformada != null && !Number.isNaN(Number(receitaInformada))
      ? Number(receitaInformada)
      : null;
  const margem = receita != null ? receita - despesa : null;

  const alerts = posts
    .filter((p) => Number(p.total_despesas || 0) > 0)
    .sort((a, b) => Number(b.total_despesas) - Number(a.total_despesas))
    .slice(0, 3)
    .map((p) => {
      const name = resolveFilialFromRow(p);
      return enrichAlert(
        {
          severity: "ALTO",
          title: `Despesa elevada: ${name}`,
          detail: formatCurrency(p.total_despesas),
          view: "expenses",
          origin: "Financeiro",
        },
        {
          why: "Despesa acima da média da rede",
          where: name,
          actionNow: `Abrir despesas filtradas por ${name}`,
        }
      );
    });

  const kpis = [
    {
      label: "Receita",
      value: receita != null ? moneyKpi(receita) : (options.resilience?.source === "degraded" ? "INTEGRATION_PROTECTED" : "Dados indisponíveis"),
      trendPct: null,
      status: "ok",
    },
    { label: "Despesa", value: moneyKpi(despesa), trendPct: null, status: "warn" },
    {
      label: "Margem",
      value: margem != null ? moneyKpi(margem) : (options.resilience?.source === "degraded" ? "INTEGRATION_PROTECTED" : "Dados indisponíveis"),
      trendPct: null,
      status: margem == null ? "ok" : margem >= 0 ? "ok" : "crit",
    },
    {
      label: "Alertas",
      value: String(alerts.length),
      trendPct: null,
      status: alerts.length ? "crit" : "ok",
    },
  ];

  const topPost = posts
    .filter((p) => Number(p.total_despesas || 0) > 0)
    .sort((a, b) => Number(b.total_despesas) - Number(a.total_despesas))[0];
  const topPostName = topPost ? resolveFilialFromRow(topPost) : null;
  const postsComDespesa = posts.filter((p) => Number(p.total_despesas || 0) > 0).length;

  const brief = buildFourQuestionBrief({
    what:
      receita != null
        ? `Receita ${moneyKpi(receita)} e despesas ${moneyKpi(despesa)} no período.`
        : `Despesas ${moneyKpi(despesa)} e contas a pagar ${moneyKpi(aPagar)} no período.`,
    why:
      postsComDespesa > 0
        ? `${postsComDespesa} posto(s) com despesas relevantes pressionam o resultado.`
        : "Despesas controladas em relação à receita.",
    where: topPostName ? `${topPostName} concentra a maior saída.` : "Impacto financeiro distribuído.",
    actionNow: topPostName
      ? `Investigar despesas de ${topPostName} hoje.`
      : "Manter disciplina de pagamentos e recebíveis.",
  });

  const chartBars = buildChartBars(
    posts.slice(0, 7).map((p) => ({
      nome: resolveFilialFromRow(p).slice(0, 16),
      valor: p.total_despesas,
    })),
    { labelKey: "nome", valueKey: "valor", max: 7 }
  );

  const criticalBranches = mapCriticalBranches(
    posts
      .filter((p) => Number(p.total_despesas || 0) > 0)
      .sort((a, b) => Number(b.total_despesas) - Number(a.total_despesas))
      .slice(0, 3)
      .map((p) => ({
        name: resolveFilialFromRow(p),
        metric: formatCurrency(p.total_despesas),
        tag: "Despesa",
        view: "expenses",
      }))
  );

  container.innerHTML = buildExecutivePageHtml({
    title: "Receitas",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Despesas por filial no período",
    criticalBranches,
    priorityActions: mapPriorityActions(alerts, { defaultView: "expenses" }),
    risks: mapRisks(alerts.map((a) => ({ title: a.title, detail: a.why, severity: a.severity }))),
    opportunities:
      margem != null && margem > 0
        ? [{ title: "Margem positiva no período", impact: moneyKpi(margem), view: "financialIntelligence" }]
        : [],
    alerts,
    detailHtml: '<div id="cards"></div><div id="list"></div>',
    detailSummary: "Detalhamento por posto",
  });
  bindExecutiveNav(container, options.onNavigate);
  renderOverviewCards(container.querySelector("#cards"), overview);
  renderTable(
    container.querySelector("#list"),
    [
      {
        key: "empresaCodigo",
        label: "Empresa",
        type: "text",
        sortable: true,
        filter: true,
        filterType: "select",
        accessor: (row) => resolveFilialFromRow(row),
        formatter: formatMissing,
        exportFormatter: (value, row) => resolveFilialFromRow(row),
      },
      {
        key: "nome",
        label: "Posto",
        type: "text",
        sortable: true,
        truncate: true,
        filter: true,
        filterType: "select",
        accessor: (row) => resolveFilialFromRow({ ...row, filial: row.nome, empresa: row.nome }),
        formatter: formatMissing,
        exportFormatter: (value, row) => resolveFilialFromRow({ ...row, filial: row.nome, empresa: row.nome }),
      },
      {
        key: "total_despesas",
        label: "Total despesas",
        type: "currency",
        sortable: true,
        formatter: formatCurrency,
        sum: true,
        filter: true,
      },
      {
        key: "total_a_pagar",
        label: "Total a pagar",
        type: "currency",
        sortable: true,
        formatter: formatCurrency,
        sum: true,
        filter: true,
      },
    ],
    posts,
    {
      state: options.tableState,
      onSearchChange: options.onSearchChange,
      onSortChange: options.onSortChange,
      onRefresh: options.onRefresh,
      onPageChange: options.onPageChange,
      emptyMessage: "Nenhum posto retornado para o filtro atual.",
      showClearFilters: true,
      onClearFilters: options.onClearFilters,
      title: "Receitas",
      exportName: options.exportName || "dashboard_financeiro",
      pdfDescription: "Visão geral financeira da rede.",
    }
  );
}
