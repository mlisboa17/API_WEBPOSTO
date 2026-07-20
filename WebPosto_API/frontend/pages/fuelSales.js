import { renderTable } from "../components/table.js";
import { formatCurrency, formatDate, formatMissing } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";
import { bindExecutiveNav, renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";
import {
  bindSectionRetry,
  friendlySectionError,
  renderSectionError,
  renderSectionSkeleton,
} from "../components/sectionState.js";

function formatDecimalBr(num, decimals = 1) {
  const n = Number(num);
  if (!Number.isFinite(n)) return "Dados indisponíveis";
  return `${n.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} L`;
}

function kpiLitros(value, hasData) {
  if (!hasData || value == null) return "Dados indisponíveis";
  return formatDecimalBr(value);
}

function kpiMoney(value, hasData) {
  if (!hasData || value == null) return "Dados indisponíveis";
  return moneyKpi(value);
}

function aggregateByFilial(rows, valueKey) {
  const byFilial = {};
  rows.forEach((row) => {
    const name = resolveFilialFromRow(row);
    if (!name) return;
    byFilial[name] = (byFilial[name] || 0) + Number(row[valueKey] || 0);
  });
  return byFilial;
}

const FUEL_EMPTY_MSG = "Integração protegida ou sem movimentação no período.";

export function renderFuelSales(container, payload, onPageChange, options = {}) {
  if (!container) return;

  const sectionUi = options.sectionUi || {};

  if (sectionUi.status === "loading") {
    container.innerHTML = renderSectionSkeleton({ title: "Carregando vendas do período…", lines: 4 });
    return;
  }

  if (sectionUi.status === "error") {
    container.innerHTML = renderSectionError({
      title: "Vendas indisponíveis",
      message: friendlySectionError(sectionUi.error, "as vendas"),
      retryId: "salesSectionRetry",
    });
    bindSectionRetry(container, "salesSectionRetry", options.onRetry);
    return;
  }

  window.salesActiveSubview = window.salesActiveSubview || "detailed";

  const rows = payload?.data || [];
  const fuelSummary = options.fuelSummary || [];
  const hasSales = rows.length > 0;
  const hasFuelSummary = fuelSummary.length > 0;
  const hasData = hasSales || hasFuelSummary;

  if (!payload || !hasData) {
    container.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Vendas",
      message: FUEL_EMPTY_MSG,
      chartTitle: "Faturamento por filial",
    });
    return;
  }

  const page = payload.page || 1;
  const limit = payload.limit || 50;
  const total = payload.total || 0;

  const totalReceita = rows.reduce((acc, row) => acc + Number(row.totalVenda || 0), 0);
  const totalLitros = fuelSummary.reduce((acc, f) => acc + Number(f.litros || 0), 0);
  const totalFaturamentoFuels = fuelSummary.reduce((acc, f) => acc + Number(f.valor || 0), 0);
  const precoMedio = totalLitros > 0 ? totalFaturamentoFuels / totalLitros : null;

  const byFilial = aggregateByFilial(rows, "totalVenda");
  const topFilial = Object.entries(byFilial).sort((a, b) => b[1] - a[1])[0];
  const alertCount = topFilial && Object.keys(byFilial).length > 1 ? 1 : 0;

  const kpis = [
    {
      label: "Vendas",
      value: hasSales ? kpiMoney(totalReceita, true) : hasFuelSummary ? kpiMoney(totalFaturamentoFuels, true) : "Dados indisponíveis",
      trendPct: null,
      status: "ok",
    },
    {
      label: "Volume",
      value: hasFuelSummary ? kpiLitros(totalLitros, true) : "Dados indisponíveis",
      trendPct: null,
      status: "ok",
    },
    {
      label: "Preço médio",
      value: precoMedio != null ? moneyKpi(precoMedio) : "Dados indisponíveis",
      trendPct: null,
      status: "ok",
    },
    {
      label: "Alertas",
      value: countKpi(alertCount),
      trendPct: null,
      status: alertCount > 0 ? "warn" : "ok",
    },
  ];

  const brief = buildFourQuestionBrief({
    what: hasData
      ? `Vendas de combustíveis totalizam ${kpis[0].value} no período.`
      : "Sem movimentação de vendas registrada no período.",
    why: topFilial ? `${topFilial[0]} concentra o maior faturamento.` : "Volume distribuído entre filiais.",
    where: topFilial ? topFilial[0] : "Rede consolidada",
    actionNow: topFilial ? `Revisar desempenho de ${topFilial[0]} hoje.` : "Manter acompanhamento do mix de vendas.",
  });

  const chartSource = hasSales
    ? Object.entries(byFilial)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 7)
        .map(([label, valor]) => ({ label, valor }))
    : fuelSummary.slice(0, 7).map((f) => ({
        label: (f.combustivelDisplay || f.combustivel || "Produto").slice(0, 16),
        valor: f.valor,
      }));

  const chartBars = buildChartBars(chartSource, { labelKey: "label", valueKey: "valor", max: 7 });

  const alerts = [];
  if (topFilial) {
    alerts.push(
      enrichAlert(
        {
          severity: "MÉDIO",
          title: `Maior faturamento — ${topFilial[0]}`,
          detail: formatCurrency(topFilial[1]),
          view: "sales",
          origin: "Vendas",
        },
        {
          why: "Concentração acima da média da rede",
          where: topFilial[0],
          actionNow: "Analisar mix e volume na filial",
        }
      )
    );
  }
  const lowParticipation = [...fuelSummary]
    .filter((f) => Number(f.participacao || 0) > 0 && Number(f.participacao || 0) < 10)
    .slice(0, 2);
  lowParticipation.forEach((f) => {
    alerts.push(
      enrichAlert(
        {
          severity: "MÉDIO",
          title: `Mix baixo — ${f.combustivelDisplay || f.combustivel}`,
          detail: `${f.participacao ?? 0}% de participação`,
          view: "sales",
          origin: "Vendas",
        },
        {
          why: "Participação abaixo de 10% no período",
          where: "Rede",
          actionNow: "Avaliar campanha comercial do produto",
        }
      )
    );
  });

  const detailShell = `
    <nav class="subtabs sales-subtabs">
      <button type="button" id="btnSubtabDetailed" class="area-tab">Detalhado</button>
      <button type="button" id="btnSubtabFuels" class="area-tab">Por combustível</button>
    </nav>
    <div id="salesSubContent"></div>
  `;

  container.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Vendas",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Faturamento por filial",
    criticalBranches: mapCriticalBranches(
      Object.entries(byFilial)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([name, val]) => ({
          name,
          metric: formatCurrency(val),
          tag: "Faturamento",
          view: "sales",
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
    detailHtml: detailShell,
    detailSummary: "Detalhamento de vendas",
  });

  bindExecutiveNav(container, options.onNavigate);

  const btnDetailed = container.querySelector("#btnSubtabDetailed");
  const btnFuels = container.querySelector("#btnSubtabFuels");
  const subContentNode = container.querySelector("#salesSubContent");
  if (!btnDetailed || !btnFuels || !subContentNode) return;

  function renderSubView() {
    btnDetailed.classList.toggle("active", window.salesActiveSubview === "detailed");
    btnFuels.classList.toggle("active", window.salesActiveSubview === "fuels");
    subContentNode.innerHTML = "";

    if (window.salesActiveSubview === "detailed") {
      const tableDiv = document.createElement("div");
      tableDiv.id = "table";
      const pagerDiv = document.createElement("div");
      pagerDiv.id = "pager";
      subContentNode.appendChild(tableDiv);
      subContentNode.appendChild(pagerDiv);

      renderTable(
        tableDiv,
        [
          { key: "data", label: "Data", type: "date", sortable: true, formatter: formatDate, filter: true },
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
          { key: "vendaCodigo", label: "Venda", type: "text", sortable: true, formatter: formatMissing, filter: true },
          { key: "cliente", label: "Cliente", type: "text", sortable: true, truncate: true, formatter: formatMissing, filter: true },
          { key: "itens", label: "Itens", type: "number", sortable: true, formatter: formatMissing, sum: true, filter: true },
          { key: "formaPagamento", label: "Forma pagamento", type: "text", sortable: true, formatter: formatMissing, filter: true, filterType: "select" },
          { key: "totalVenda", label: "Total venda", type: "currency", sortable: true, formatter: formatCurrency, sum: true, filter: true },
        ],
        rows,
        {
          state: options.tableState,
          onSearchChange: options.onSearchChange,
          onSortChange: options.onSortChange,
          onRefresh: options.onRefresh,
          onPageChange: onPageChange,
          pagination: { page, limit, total },
          emptyMessage: "Nenhuma venda encontrada para os filtros informados.",
          showClearFilters: true,
          onClearFilters: options.onClearFilters,
          title: "Lançamentos",
          exportName: options.exportName || `vendas_${String(rows[0]?.data || new Date().toISOString().slice(0, 10))}`,
          pdfDescription: "Vendas detalhadas por filial para o período filtrado.",
        }
      );
      return;
    }

    const fuelTableDiv = document.createElement("div");
    fuelTableDiv.id = "fuelTable";
    subContentNode.appendChild(fuelTableDiv);

    renderTable(
      fuelTableDiv,
      [
        {
          key: "combustivel",
          label: "Combustível",
          type: "text",
          sortable: true,
          filter: true,
          accessor: (row) => row?.combustivelDisplay || row?.combustivel,
          exportFormatter: (value, row) => row?.combustivelDisplay || value,
        },
        { key: "litros", label: "Litros vendidos", type: "number", sortable: true, formatter: (v) => formatDecimalBr(v, 1), sum: true },
        { key: "valor", label: "Faturamento", type: "currency", sortable: true, formatter: formatCurrency, sum: true },
        { key: "ticketMedioLitro", label: "Preço médio litro", type: "currency", sortable: true, formatter: formatCurrency },
        { key: "participacao", label: "Participação", type: "number", sortable: true, formatter: (v) => `${v}%` },
      ],
      fuelSummary,
      {
        state: options.tableState,
        onRefresh: options.onRefresh,
        emptyMessage: "Nenhum combustível retornado para o período selecionado.",
        title: "Mix por combustível",
        exportName: `vendas_combustiveis_${options.exportName || new Date().toISOString().slice(0, 10)}`,
        pdfDescription: "Volume e faturamento por produto no período filtrado.",
      }
    );
  }

  btnDetailed.addEventListener("click", () => {
    window.salesActiveSubview = "detailed";
    renderSubView();
  });
  btnFuels.addEventListener("click", () => {
    window.salesActiveSubview = "fuels";
    renderSubView();
  });

  renderSubView();
}
