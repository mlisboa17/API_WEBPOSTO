import { renderTable } from "../components/table.js";
import { formatCurrency, formatDate, formatMissing } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";
import { EXPENSE_NATURE_OPTIONS } from "../components/NatureMultiSelectLogos.js";
import { MANAGEMENT_GROUP_OPTIONS } from "../components/ManagementMultiSelectLogos.js";
import { bindExecutiveNav } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapPriorityActions,
  mapRisks,
  topFilialByField,
} from "../services/executiveBrief.js";

function formatNature(value, row) {
  if (row?.expenseNatureLabel) return row.expenseNatureLabel;
  const opt = EXPENSE_NATURE_OPTIONS.find((o) => o.value === value);
  return opt?.label || formatMissing(value);
}

function formatSubNature(value) {
  if (!value) return "—";
  return String(value).replace(/_/g, " ");
}

function renderNatureCards(resumoPorNatureza) {
  const cards = EXPENSE_NATURE_OPTIONS.map((opt) => {
    const info = resumoPorNatureza[opt.value] || { count: 0, valor: "0", pct: 0 };
    return `
      <div class="expense-nature-card" data-nature="${opt.value}">
        <div class="expense-nature-card__label">${opt.label}</div>
        <div class="expense-nature-card__valor">${formatCurrency(info.valor)}</div>
        <div class="expense-nature-card__meta">${info.count} reg. · ${info.pct ?? 0}%</div>
      </div>
    `;
  }).join("");
  return `<div class="expense-nature-cards">${cards}</div>`;
}

function renderManagementCards(resumoPorGrupoGerencial, employeeBalanceCard) {
  const cards = MANAGEMENT_GROUP_OPTIONS.map((opt) => {
    const info = resumoPorGrupoGerencial[opt.value] || { count: 0, valor: "0", pct: 0 };
    return `
      <div class="expense-mgmt-card" data-mgmt-group="${opt.value}">
        <div class="expense-mgmt-card__label">${opt.label}</div>
        <div class="expense-mgmt-card__valor">${formatCurrency(info.valor)}</div>
        <div class="expense-mgmt-card__meta">${info.count} reg. · ${info.pct ?? 0}%</div>
      </div>
    `;
  }).join("");

  const balance = employeeBalanceCard || {};
  const balanceCard = `
    <div class="expense-mgmt-card expense-mgmt-card--balance">
      <div class="expense-mgmt-card__label">Saldo Funcionários</div>
      <div class="expense-mgmt-card__valor">${balance.credores ?? 0} cred. · ${balance.devedores ?? 0} dev.</div>
      <div class="expense-mgmt-card__meta">
        Médio ${formatCurrency(balance.saldoMedio ?? 0)}
        ${balance.principalDevedor ? ` · Dev. ${balance.principalDevedor}` : ""}
      </div>
    </div>
  `;

  return `<div class="expense-mgmt-cards">${cards}${balanceCard}</div>`;
}

function formatEmployee(_value, row) {
  if (row?.employeeName) return row.employeeName;
  const cod = row?.funcionarioCodigo;
  if (cod != null && cod !== "") return `Cód. ${cod}`;
  return "—";
}

function formatMgmtGroup(value, row) {
  return row?.expenseManagementGroupLabel || formatMissing(value);
}

function formatMgmtClass(value, row) {
  return row?.expenseManagementClassLabel || formatMissing(value);
}

function sumExpenses(rows) {
  return rows.reduce((acc, row) => acc + Number(row?.valor || 0), 0);
}

export function renderExpenses(container, payload, onPageChange, options = {}) {
  const rows = payload?.data || [];
  const page = payload?.page || 1;
  const limit = payload?.limit || 50;
  const total = payload?.total || 0;
  const resumoPorNatureza = payload?.resumoPorNatureza || {};
  const resumoPorGrupoGerencial = payload?.resumoPorGrupoGerencial || {};
  const employeeBalanceCard = payload?.employeeCashLedger?.employeeBalanceCard || null;
  const filters = options.filters || {};

  const totalDespesa = payload?.totalValor ?? sumExpenses(rows);
  const topNature = Object.entries(resumoPorNatureza)
    .map(([key, info]) => ({ key, valor: Number(info?.valor || 0), label: key }))
    .sort((a, b) => b.valor - a.valor)[0];
  const alertasCount = topNature && topNature.valor > 0 ? 1 : 0;

  const kpis = [
    { label: "Receita", value: "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Despesa", value: moneyKpi(totalDespesa), trendPct: null, status: "warn" },
    { label: "Margem", value: "Dados indisponíveis", trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: String(Object.keys(resumoPorNatureza).length || alertasCount),
      trendPct: null,
      status: alertasCount ? "crit" : "ok",
    },
  ];

  const topNatureLabel =
    EXPENSE_NATURE_OPTIONS.find((o) => o.value === topNature?.key)?.label || topNature?.key || "Não informado";
  const topFilial = topFilialByField(rows, (row) => resolveFilialFromRow(row));

  const brief = buildFourQuestionBrief({
    what: `Saída de caixa de ${moneyKpi(totalDespesa)} registrada no período.`,
    why: topNature
      ? `${topNatureLabel} concentra ${formatCurrency(topNature.valor)} — principal driver de custo.`
      : "Despesas distribuídas sem concentração dominante.",
    where: topFilial ? `${topFilial.name} é a filial com maior volume.` : "Impacto distribuído entre filiais.",
    actionNow: topNature
      ? `Auditar ${topNatureLabel} hoje${topFilial ? ` em ${topFilial.name}` : ""}.`
      : "Filtrar lançamentos acima da média e validar com gestores.",
  });

  const chartBars = buildChartBars(
    Object.entries(resumoPorNatureza).map(([key, info]) => ({
      label: EXPENSE_NATURE_OPTIONS.find((o) => o.value === key)?.label || key,
      valor: info?.valor,
    })),
    { labelKey: "label", valueKey: "valor", max: 6 }
  );

  const alerts = Object.entries(resumoPorNatureza)
    .sort((a, b) => Number(b[1]?.valor || 0) - Number(a[1]?.valor || 0))
    .slice(0, 3)
    .map(([key, info]) => {
      const label = EXPENSE_NATURE_OPTIONS.find((o) => o.value === key)?.label || key;
      return enrichAlert(
        {
          severity: Number(info?.pct || 0) > 30 ? "ALTO" : "MÉDIO",
          title: `Despesa ${label}`,
          detail: `${formatCurrency(info?.valor)} · ${info?.count ?? 0} registros`,
          view: "",
          origin: "Financeiro",
        },
        {
          why: `${info?.pct ?? 0}% do total de despesas`,
          where: topFilial?.name || "Rede",
          actionNow: `Revisar lançamentos de ${label} hoje`,
        }
      );
    });

  const filialRows = Object.entries(
    rows.reduce((acc, row) => {
      const name = resolveFilialFromRow(row);
      acc[name] = (acc[name] || 0) + Number(row.valor || 0);
      return acc;
    }, {})
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name, valor]) => ({ name, metric: formatCurrency(valor), tag: "Despesa", view: "" }));

  const natureCardsHtml = Object.keys(resumoPorNatureza).length ? renderNatureCards(resumoPorNatureza) : "";
  const mgmtCardsHtml = Object.keys(resumoPorGrupoGerencial).length
    ? renderManagementCards(resumoPorGrupoGerencial, employeeBalanceCard)
    : "";

  const columns = [
    { key: "data", label: "Data", type: "date", sortable: true, formatter: formatDate, filter: true },
    { key: "valor", label: "Valor", type: "currency", sortable: true, formatter: formatCurrency, sum: true, filter: true },
    { key: "descricao", label: "Descrição", type: "text", sortable: true, truncate: true, filter: true, searchable: true },
    {
      key: "employeeName",
      label: "Funcionário",
      type: "text",
      sortable: true,
      formatter: formatEmployee,
      exportFormatter: (_v, row) => formatEmployee(null, row),
      filter: true,
      searchable: true,
      accessor: (row) => formatEmployee(null, row),
    },
    {
      key: "expenseNature",
      label: "Natureza",
      type: "text",
      sortable: true,
      formatter: formatNature,
      exportFormatter: (v, row) => formatNature(v, row),
      filter: true,
      filterType: "select",
    },
    {
      key: "expenseManagementGroup",
      label: "Grupo Gerencial",
      type: "text",
      sortable: true,
      formatter: formatMgmtGroup,
      exportFormatter: (v, row) => formatMgmtGroup(v, row),
      filter: true,
      filterType: "select",
    },
    {
      key: "filial",
      label: "Empresa",
      type: "text",
      sortable: true,
      filter: true,
      filterType: "select",
      accessor: (row) => resolveFilialFromRow(row),
      formatter: formatMissing,
      exportFormatter: (value, row) => resolveFilialFromRow(row),
      searchable: true,
    },
    { key: "fornecedor", label: "Fornecedor", type: "text", sortable: true, truncate: true, formatter: formatMissing, filter: true },
    { key: "centroCusto", label: "Centro Custo", type: "text", sortable: true, truncate: true, formatter: formatMissing, filter: true, filterType: "select" },
  ];

  const natureSummaryRows = EXPENSE_NATURE_OPTIONS.map((opt) => {
    const info = resumoPorNatureza[opt.value] || { count: 0, valor: "0", pct: 0 };
    return { natureza: opt.label, registros: info.count, valor: info.valor, pct: `${info.pct ?? 0}%` };
  });

  container.innerHTML = buildExecutivePageHtml({
    title: "Despesas",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Despesas por natureza",
    criticalBranches: mapCriticalBranches(filialRows),
    priorityActions: mapPriorityActions(
      alerts.map((a) => ({ title: a.title, detail: a.actionNow, view: a.view }))
    ),
    risks: mapRisks(
      alerts.map((a) => ({ title: a.title, detail: a.why, severity: a.severity }))
    ),
    opportunities: [],
    alerts,
    detailHtml: `${natureCardsHtml}${mgmtCardsHtml}<div id="table"></div><div id="pager"></div>`,
    detailSummary: "Detalhamento de despesas",
  });

  bindExecutiveNav(container, options.onNavigate);

  renderTable(container.querySelector("#table"), columns, rows, {
    state: options.tableState,
    onSearchChange: options.onSearchChange,
    onSortChange: options.onSortChange,
    onRefresh: options.onRefresh,
    onPageChange: onPageChange,
    pagination: { page, limit, total },
    emptyMessage: "Nenhuma despesa encontrada para os filtros informados.",
    showClearFilters: true,
    onClearFilters: options.onClearFilters,
    title: "Lançamentos",
    exportName: options.exportName || `despesas_${String(rows[0]?.data || new Date().toISOString().slice(0, 10))}`,
    pdfDescription: "Despesas com classificação gerencial por natureza e filial.",
    pdfNatureSummary: natureSummaryRows,
  });
}
