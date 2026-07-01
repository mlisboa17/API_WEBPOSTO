import { renderTable } from "../components/table.js";
import { formatCurrency, formatDate, formatMissing } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";
import { renderExecutiveTablePage } from "../services/executiveCockpitAdapter.js";

export function renderAccountsPayable(container, payload, onPageChange, options = {}) {
  const rows = payload?.data || [];
  const page = payload?.page || 1;
  const limit = payload?.limit || 50;
  const total = payload?.total || 0;
  const filters = options.filters || {};

  renderExecutiveTablePage(container, payload, filters, {
    title: "Contas a Pagar",
    valueKey: "valor",
    formatTotal: (n) => formatCurrency(n),
    filialAccessor: (row) => resolveFilialFromRow(row),
    chartTitle: "Pagamentos por filial",
    branchTag: "Contas",
    defaultView: "accounts",
    detailBuilder: () => '<div id="accountsTable"></div><div id="accountsPager"></div>',
    onNavigate: options.onNavigate,
  });

  const tableNode = container.querySelector("#accountsTable");
  if (!tableNode) return;

  renderTable(
    tableNode,
    [
      { key: "fornecedor", label: "Fornecedor", type: "text", sortable: true, truncate: true, formatter: formatMissing, filter: true },
      { key: "valor", label: "Valor", type: "currency", sortable: true, formatter: formatCurrency, sum: true, filter: true },
      { key: "vencimento", label: "Vencimento", type: "date", sortable: true, formatter: formatDate, filter: true },
      {
        key: "filial",
        label: "Filial",
        type: "text",
        sortable: true,
        filter: true,
        filterType: "select",
        accessor: (row) => resolveFilialFromRow(row),
        formatter: formatMissing,
        exportFormatter: (value, row) => resolveFilialFromRow(row),
      },
      { key: "status", label: "Status", type: "status", sortable: true, formatter: formatMissing, filter: true, filterType: "select" },
    ],
    rows,
    {
      state: options.tableState,
      onSearchChange: options.onSearchChange,
      onSortChange: options.onSortChange,
      onRefresh: options.onRefresh,
      onPageChange: onPageChange,
      pagination: { page, limit, total },
      emptyMessage: "Nenhuma conta a pagar encontrada.",
      showClearFilters: true,
      onClearFilters: options.onClearFilters,
      title: "Contas a Pagar",
      exportName: options.exportName || `contas_pagar_${String(rows[0]?.vencimento || new Date().toISOString().slice(0, 10))}`,
      pdfDescription: "Contas a pagar filtradas da visão atual.",
    }
  );
}
