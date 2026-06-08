import { renderOverviewCards } from "../components/cards.js";
import { renderTable } from "../components/table.js";
import { formatCurrency } from "../services/format.js";
import { formatMissing } from "../services/formatters.js";
import { resolveFilialFromRow } from "../components/filiais.js";

export function renderDashboard(container, overview, options = {}) {
  const posts = overview?.postos || [];

  container.innerHTML = '<div id="cards"></div><div id="list"></div>';
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
      { key: "total_despesas", label: "Total despesas", type: "currency", sortable: true, formatter: formatCurrency, sum: true, filter: true },
      { key: "total_a_pagar", label: "Total a pagar", type: "currency", sortable: true, formatter: formatCurrency, sum: true, filter: true },
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
      title: "Dashboard Financeiro",
      exportName: options.exportName || "dashboard_financeiro",
      pdfDescription: "Visão geral financeira da rede.",
    }
  );
}
