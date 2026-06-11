import { renderTable } from "../components/table.js";
import { formatCurrency, formatDate, formatMissing } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";
import { EXPENSE_NATURE_OPTIONS } from "../components/NatureMultiSelectLogos.js";
import { MANAGEMENT_GROUP_OPTIONS } from "../components/ManagementMultiSelectLogos.js";

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

function formatMgmtGroup(value, row) {
  return row?.expenseManagementGroupLabel || formatMissing(value);
}

function formatMgmtClass(value, row) {
  return row?.expenseManagementClassLabel || formatMissing(value);
}

export function renderExpenses(container, payload, onPageChange, options = {}) {
  const rows = payload?.data || [];
  const page = payload?.page || 1;
  const limit = payload?.limit || 50;
  const total = payload?.total || 0;
  const resumoPorNatureza = payload?.resumoPorNatureza || {};
  const resumoPorGrupoGerencial = payload?.resumoPorGrupoGerencial || {};
  const employeeBalanceCard = payload?.employeeCashLedger?.employeeBalanceCard || null;

  const natureCardsHtml = Object.keys(resumoPorNatureza).length ? renderNatureCards(resumoPorNatureza) : "";
  const mgmtCardsHtml = Object.keys(resumoPorGrupoGerencial).length
    ? renderManagementCards(resumoPorGrupoGerencial, employeeBalanceCard)
    : "";
  const cardsHtml = `${natureCardsHtml}${mgmtCardsHtml}`;

  const columns = [
    { key: "data", label: "Data", type: "date", sortable: true, formatter: formatDate, filter: true },
    { key: "valor", label: "Valor", type: "currency", sortable: true, formatter: formatCurrency, sum: true, filter: true },
    { key: "descricao", label: "Descrição", type: "text", sortable: true, truncate: true, filter: true, searchable: true },
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
      key: "expenseSubNature",
      label: "Subnatureza",
      type: "text",
      sortable: true,
      formatter: formatSubNature,
      exportFormatter: formatSubNature,
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
      key: "expenseManagementClass",
      label: "Classe Gerencial",
      type: "text",
      sortable: true,
      formatter: formatMgmtClass,
      exportFormatter: (v, row) => formatMgmtClass(v, row),
      filter: true,
      filterType: "select",
    },
    {
      key: "dreImpact",
      label: "DRE",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    {
      key: "cashFlowImpact",
      label: "Caixa",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    {
      key: "origem",
      label: "Origem",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    { key: "fornecedor", label: "Fornecedor", type: "text", sortable: true, truncate: true, formatter: formatMissing, filter: true },
    { key: "planoConta", label: "Plano Conta", type: "text", sortable: true, truncate: true, formatter: formatMissing, filter: true },
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
    {
      key: "origemReal",
      label: "Origem Real",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    {
      key: "origemTecnica",
      label: "Origem Técnica",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    {
      key: "categoriaOperacional",
      label: "Cat. Operacional",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    { key: "documento", label: "Documento", type: "text", sortable: true, formatter: formatMissing, filter: true },
    {
      key: "lineageConfidence",
      label: "Confiança Linhagem",
      type: "number",
      sortable: true,
      formatter: (v) => (v == null ? "—" : `${v}%`),
      filter: true,
    },
    {
      key: "semanticConfidence",
      label: "Confiança Semântica",
      type: "number",
      sortable: true,
      formatter: (v) => (v == null ? "—" : `${v}%`),
      filter: true,
    },
    {
      key: "categoria",
      label: "Categoria",
      type: "text",
      sortable: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    {
      key: "centroCusto",
      label: "Centro Custo",
      type: "text",
      sortable: true,
      truncate: true,
      formatter: formatMissing,
      filter: true,
      filterType: "select",
    },
    { key: "pdvCodigo", label: "PDV", type: "text", sortable: true, formatter: formatMissing, filter: true },
    { key: "turno", label: "Turno", type: "text", sortable: true, formatter: formatMissing, filter: true },
    { key: "funcionarioCodigo", label: "Operador", type: "text", sortable: true, formatter: formatMissing, filter: true },
  ];

  const natureSummaryRows = EXPENSE_NATURE_OPTIONS.map((opt) => {
    const info = resumoPorNatureza[opt.value] || { count: 0, valor: "0", pct: 0 };
    return { natureza: opt.label, registros: info.count, valor: info.valor, pct: `${info.pct ?? 0}%` };
  });

  container.innerHTML = `${cardsHtml}<div id="table"></div><div id="pager"></div>`;
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
    title: "Despesas",
    exportName: options.exportName || `despesas_${String(rows[0]?.data || new Date().toISOString().slice(0, 10))}`,
    pdfDescription:
      "Despesas com classificação semântica e gerencial (Employee Cash Ledger F03.3).",
    pdfNatureSummary: natureSummaryRows,
  });
}
