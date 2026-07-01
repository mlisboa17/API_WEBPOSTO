import { renderTable } from "../components/table.js";
import { formatMissing, formatNumber } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";
import { bindExecutiveNav, renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

function kpiQty(value, hasData) {
  if (!hasData || value == null) return "Dados indisponíveis";
  return formatNumber(value);
}

const FUEL_EMPTY_MSG = "Integração protegida ou sem movimentação no período.";

function aggregateByFilial(rows) {
  const byFilial = {};
  rows.forEach((row) => {
    const name = resolveFilialFromRow(row);
    if (!name) return;
    byFilial[name] = (byFilial[name] || 0) + Number(row.quantidade || 0);
  });
  return byFilial;
}

export function renderFuelInventory(container, payload, onPageChange, options = {}) {
  if (!container) return;

  if (!payload) {
    container.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Estoque",
      message: FUEL_EMPTY_MSG,
      chartTitle: "Estoque por filial",
    });
    return;
  }

  const rows = payload.data || [];
  const page = payload.page || 1;
  const limit = payload.limit || 50;
  const total = payload.total || 0;
  const hasData = rows.length > 0;

  if (!hasData) {
    container.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Estoque",
      message: FUEL_EMPTY_MSG,
      chartTitle: "Estoque por filial",
    });
    return;
  }

  const estoqueTotal = rows.reduce((acc, row) => acc + Number(row.quantidade || 0), 0);
  const byFilial = aggregateByFilial(rows);
  const filiaisCount = Object.keys(byFilial).length;
  const produtosCount = new Set(rows.map((r) => r.codigo || r.descricaoDisplay || r.descricao).filter(Boolean)).size;
  const topFilial = Object.entries(byFilial).sort((a, b) => b[1] - a[1])[0];
  const lowFilial = Object.entries(byFilial).sort((a, b) => a[1] - b[1])[0];

  const kpis = [
    { label: "Estoque total", value: kpiQty(estoqueTotal, hasData), trendPct: null, status: "ok" },
    { label: "Filiais", value: hasData ? countKpi(filiaisCount) : "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Produtos", value: hasData ? countKpi(produtosCount) : "Dados indisponíveis", trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: hasData && lowFilial && filiaisCount > 1 ? "1" : "0",
      trendPct: null,
      status: lowFilial && filiaisCount > 1 ? "warn" : "ok",
    },
  ];

  const brief = buildFourQuestionBrief({
    what: hasData
      ? `Estoque consolidado de ${kpiQty(estoqueTotal, true)} em ${filiaisCount} filial(is).`
      : "Sem registros de estoque no período.",
    why: topFilial ? `${topFilial[0]} concentra o maior volume em tanques.` : "Distribuição entre filiais.",
    where: topFilial ? topFilial[0] : "Rede consolidada",
    actionNow: lowFilial && filiaisCount > 1 ? `Verificar nível em ${lowFilial[0]}.` : "Manter monitoramento de tanques.",
  });

  const chartBars = buildChartBars(
    Object.entries(byFilial)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 7)
      .map(([label, valor]) => ({ label, valor })),
    { labelKey: "label", valueKey: "valor", max: 7 }
  );

  const alerts = [];
  if (lowFilial && filiaisCount > 1 && Number(lowFilial[1]) >= 0) {
    alerts.push(
      enrichAlert(
        {
          severity: "MÉDIO",
          title: `Estoque reduzido — ${lowFilial[0]}`,
          detail: formatNumber(lowFilial[1]),
          view: "stock",
          origin: "Estoque",
        },
        {
          why: "Menor volume entre as filiais do recorte",
          where: lowFilial[0],
          actionNow: "Validar reposição e nível de tanques",
        }
      )
    );
  }
  if (topFilial && filiaisCount > 1) {
    alerts.push(
      enrichAlert(
        {
          severity: "MÉDIO",
          title: `Maior estoque — ${topFilial[0]}`,
          detail: formatNumber(topFilial[1]),
          view: "stock",
          origin: "Estoque",
        },
        {
          why: "Concentração acima da média",
          where: topFilial[0],
          actionNow: "Revisar giro e capacidade",
        }
      )
    );
  }

  container.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Estoque",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Estoque por filial",
    criticalBranches: mapCriticalBranches(
      Object.entries(byFilial)
        .sort((a, b) => a[1] - b[1])
        .slice(0, 3)
        .map(([name, val]) => ({
          name,
          metric: formatNumber(val),
          tag: "Estoque baixo",
          view: "stock",
        }))
    ),
    priorityActions: mapPriorityActions(
      alerts.slice(0, 3).map((a) => ({ title: a.title, detail: a.why, view: a.view }))
    ),
    risks: mapRisks(
      alerts.slice(0, 3).map((a) => ({ title: a.title, detail: a.why, severity: a.severity }))
    ),
    opportunities: [],
    alerts: alerts.slice(0, 3),
    detailHtml: '<div id="stockTable"></div><div id="stockPager"></div>',
    detailSummary: "Detalhamento de estoque",
  });

  bindExecutiveNav(container, options.onNavigate);

  const tableNode = container.querySelector("#stockTable");
  if (!tableNode) return;

  renderTable(
    tableNode,
    [
      {
        key: "filial",
        label: "Filial",
        type: "text",
        sortable: true,
        truncate: true,
        filter: true,
        filterType: "select",
        accessor: (row) => resolveFilialFromRow(row),
        formatter: formatMissing,
        exportFormatter: (value, row) => resolveFilialFromRow(row),
      },
      { key: "tipoRegistro", label: "Tipo", type: "text", sortable: true, formatter: formatMissing, filter: true, filterType: "select" },
      { key: "codigo", label: "Código", type: "text", sortable: true, formatter: formatMissing, filter: true },
      {
        key: "descricao",
        label: "Descrição",
        type: "text",
        sortable: true,
        truncate: true,
        filter: true,
        accessor: (row) => row?.descricaoDisplay || row?.descricao,
        formatter: formatMissing,
        exportFormatter: (value, row) => row?.descricaoDisplay || value,
      },
      { key: "unidade", label: "Unidade", type: "text", sortable: true, formatter: formatMissing, filter: true, filterType: "select" },
      { key: "quantidade", label: "Quantidade", type: "number", sortable: true, formatter: formatNumber, sum: true, filter: true },
    ],
    rows,
    {
      state: options.tableState,
      onSearchChange: options.onSearchChange,
      onSortChange: options.onSortChange,
      onRefresh: options.onRefresh,
      onPageChange: onPageChange,
      pagination: { page, limit, total },
      emptyMessage: "Nenhum registro de estoque retornado para os filtros informados.",
      showClearFilters: true,
      onClearFilters: options.onClearFilters,
      title: "Tanques e produtos",
      exportName: options.exportName || `estoque_${new Date().toISOString().slice(0, 10)}`,
      pdfDescription: "Estoque de produtos e tanques por filial no período filtrado.",
    }
  );
}
