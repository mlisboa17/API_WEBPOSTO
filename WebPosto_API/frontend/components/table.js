import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatMissing,
  toSearchText,
} from "../services/format.js";
import { downloadCsv, openPdfPreview } from "../services/export.js";
import { cycleSort, filterRows, getSortIndicator, sortRows } from "../services/sorting.js";
import { APP_CONFIG } from "../config.js";

function debounce(fn, delayMs) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delayMs);
  };
}

function escapeHtml(value) {
  return formatMissing(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function defaultFormatter(type, value) {
  if (type === "currency") return formatCurrency(value);
  if (type === "date") return formatDate(value);
  if (type === "number") return formatMissing(value);
  return formatMissing(value);
}

function resolveRawValue(row, column) {
  if (column.accessor) return column.accessor(row);
  return row?.[column.key];
}

function resolveCellValue(row, column) {
  const rawValue = resolveRawValue(row, column);
  const value = column.formatter
    ? column.formatter(rawValue, row)
    : defaultFormatter(column.type, rawValue);
  const title = column.title === false ? "" : formatMissing(column.tooltip ? rawValue : value);
  const className = ["cell"];
  if (column.className) className.push(column.className);
  if (column.type === "currency") className.push("cell-currency");
  if (column.type === "date") className.push("cell-date");
  if (column.truncate !== false) className.push("cell-truncate");
  return {
    value,
    title,
    className: className.join(" "),
  };
}

function renderBadge(value) {
  const normalized = toSearchText(value || "desconhecido");
  const classes = ["badge"];
  if (normalized.includes("pago")) classes.push("badge-success");
  else if (normalized.includes("pend")) classes.push("badge-warning");
  else if (normalized.includes("venc")) classes.push("badge-danger");
  else classes.push("badge-neutral");
  return classes.join(" ");
}

function parseNumericValue(value) {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;

  const raw = String(value)
    .replace(/\s/g, "")
    .replace(/R\$/g, "")
    .replace(/[^0-9,.-]/g, "");

  if (!raw) return null;

  const hasComma = raw.includes(",");
  const hasDot = raw.includes(".");

  let normalized = raw;
  if (hasComma && hasDot) {
    // pt-BR style: 1.234,56
    normalized = raw.replace(/\./g, "").replace(/,/g, ".");
  } else if (hasComma) {
    // decimal comma: 1234,56
    normalized = raw.replace(/,/g, ".");
  }

  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isNaN(parsed) ? null : parsed;
}

function isSummableColumn(column) {
  if (!column?.sum) return false;
  return column.type === "currency" || column.type === "number";
}

function formatSumValue(column, total) {
  if (column.type === "currency") return formatCurrency(total);
  return formatNumber(total);
}

function buildSumMap(rows, columns) {
  const sumColumns = columns.filter(isSummableColumn);
  if (sumColumns.length === 0) return [];

  return sumColumns.map((column) => {
    const total = rows.reduce((acc, row) => {
      const rawValue = resolveRawValue(row, column);
      const parsed = parseNumericValue(rawValue);
      return parsed === null ? acc : acc + parsed;
    }, 0);

    return {
      key: column.key,
      label: column.label,
      type: column.type,
      total,
      formatted: formatSumValue(column, total),
    };
  });
}

function buildSummaryText(prefix, sums) {
  if (!sums.length) return "";
  const details = sums.map((item) => `${item.label}: ${item.formatted}`).join(" | ");
  return `${prefix}: ${details}`;
}

function getFilterType(column) {
  if (column.filterType) return column.filterType;
  if (column.type === "currency" || column.type === "number") return "number";
  return "text";
}

function normalizeFilterValue(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item || "").trim())
      .filter(Boolean);
  }
  return String(value || "").trim();
}

function getActiveHeaderFiltersCount(headerFilters = {}) {
  return Object.values(headerFilters).filter((value) => {
    const normalized = normalizeFilterValue(value);
    if (Array.isArray(normalized)) return normalized.length > 0;
    return Boolean(normalized);
  }).length;
}

function getHeaderFilterValue(state, key) {
  return normalizeFilterValue(state?.headerFilters?.[key] || "");
}

function matchesHeaderFilter(row, column, filterValue) {
  const normalizedFilter = normalizeFilterValue(filterValue);
  if (Array.isArray(normalizedFilter) && normalizedFilter.length === 0) return true;
  if (!Array.isArray(normalizedFilter) && !normalizedFilter) return true;

  if (Array.isArray(normalizedFilter) && normalizedFilter.includes("__ALL__")) return true;
  if (!Array.isArray(normalizedFilter) && normalizedFilter === "__ALL__") return true;

  const rawValue = resolveRawValue(row, column);
  const filterType = getFilterType(column);

  if (filterType === "select") {
    const selected = Array.isArray(normalizedFilter) ? normalizedFilter : [normalizedFilter];
    return selected.some((value) => toSearchText(rawValue) === toSearchText(value));
  }

  if (filterType === "number") {
    const selected = Array.isArray(normalizedFilter) ? normalizedFilter : [normalizedFilter];
    const parsedRaw = parseNumericValue(rawValue);
    if (parsedRaw === null) return false;
    return selected.some((value) => {
      const parsedFilter = parseNumericValue(value);
      return parsedFilter !== null && parsedRaw === parsedFilter;
    });
  }

  const selected = Array.isArray(normalizedFilter) ? normalizedFilter : [normalizedFilter];
  return selected.some((value) => toSearchText(rawValue).includes(toSearchText(value)));
}

function applyHeaderFilters(rows, columns, headerFilters = {}) {
  const activeColumns = columns.filter((column) => column.filter);
  if (!activeColumns.length) return rows.slice();

  return rows.filter((row) =>
    activeColumns.every((column) => matchesHeaderFilter(row, column, headerFilters[column.key]))
  );
}

function buildSelectFilterOptions(rows, column) {
  const values = Array.from(
    new Set(
      rows
        .map((row) => resolveRawValue(row, column))
        .map((value) => formatMissing(value))
        .filter((value) => value && value !== "—")
    )
  ).sort((a, b) => a.localeCompare(b, "pt-BR"));

  return values;
}

function buildHeaderFilterCell(column, value, optionValues = []) {
  if (!column.filter) return "<th></th>";
  const filterType = getFilterType(column);
  const filterKey = escapeAttr(column.key);

  if (filterType === "select") {
    const selectedValues = Array.isArray(value) ? value : value ? [value] : [];
    const selectedSet = new Set(selectedValues.map((item) => String(item)));
    const selectedCount = selectedValues.length;
    const options = [
      '<option value="__ALL__">Todos</option>',
      ...optionValues.map((option) => {
        const selected = selectedSet.has(String(option)) ? " selected" : "";
        return `<option value="${escapeAttr(option)}"${selected}>${escapeHtml(option)}</option>`;
      }),
    ].join("");

    return `
      <th>
        <select class="header-filter" data-filter-key="${filterKey}" multiple size="4">
          ${options}
        </select>
        <div class="small">${selectedCount > 0 ? `${selectedCount} selecionada(s)` : "Todas"}</div>
      </th>
    `;
  }

  if (filterType === "number") {
    return `
      <th>
        <input
          class="header-filter"
          data-filter-key="${filterKey}"
          type="number"
          step="any"
          value="${escapeAttr(value)}"
          placeholder="Filtrar"
        />
      </th>
    `;
  }

  return `
    <th>
      <input
        class="header-filter"
        data-filter-key="${filterKey}"
        type="search"
        value="${escapeAttr(value)}"
        placeholder="Filtrar"
      />
    </th>
  `;
}

function buildToolbar(options, visibleRows, activeHeaderFiltersCount, filteredTotal, page, totalPages) {
  const pageCountText = options.pagination
    ? `Página ${page} de ${totalPages} | Total filtrado: ${filteredTotal}`
    : null;
  const visibleCountText = `${visibleRows.length} registros exibidos`;
  const filterIndicator = activeHeaderFiltersCount > 0
    ? `Filtros da tabela ativos: ${activeHeaderFiltersCount}`
    : "Nenhum filtro da tabela ativo";

  return `
    <div class="list-toolbar">
      <div class="list-toolbar__group list-toolbar__group--explore">
        <div class="list-toolbar__group-title">Exploração</div>
        <div class="list-toolbar__search">
          <label for="tableSearch">Busca rápida</label>
          <input id="tableSearch" type="search" value="${escapeAttr(options.state?.search || "")}" placeholder="Pesquisar na listagem" />
          <button type="button" data-action="clear-table-filters">Limpar filtros da tabela</button>
        </div>
      </div>
      <div class="list-toolbar__actions-wrap">
        <div class="list-toolbar__group list-toolbar__group--data">
          <div class="list-toolbar__group-title">Dados</div>
          <div class="list-toolbar__actions">
            ${options.onRefresh ? '<button type="button" data-action="refresh">Atualizar</button>' : ""}
            ${options.onClearFilters ? '<button type="button" data-action="clear">Limpar filtros</button>' : ""}
          </div>
        </div>
        <div class="list-toolbar__group list-toolbar__group--export">
          <div class="list-toolbar__group-title">Exportação</div>
          <div class="list-toolbar__actions">
            <button type="button" data-action="csv">Exportar CSV</button>
            <button type="button" data-action="pdf">Exportar PDF</button>
          </div>
        </div>
      </div>
      <div class="list-toolbar__meta">
        ${pageCountText ? `<span>${pageCountText}</span>` : ""}
        <span>${visibleCountText}</span>
        <span class="list-toolbar__filter-indicator">${escapeHtml(filterIndicator)}</span>
      </div>
    </div>
  `;
}

function buildEmptyState(options) {
  return `
    <div class="empty-state">
      <div>
        <p class="empty-state__title">${options.emptyMessage || "Nenhum resultado encontrado."}</p>
        <p class="small">${options.emptyHint || "Ajuste os filtros ou a busca para encontrar registros."}</p>
      </div>
      <div class="empty-state__actions">
        ${options.onClearFilters ? '<button type="button" data-action="clear">Limpar filtros</button>' : ""}
      </div>
    </div>
  `;
}

export function renderTable(container, columns, rows, options = {}) {
  const state = options.state || { search: "", sort: null, headerFilters: {} };
  if (!state.headerFilters) state.headerFilters = {};

  const quickSearchRows = filterRows(rows || [], columns, state.search);
  const headerFilteredRows = applyHeaderFilters(quickSearchRows, columns, state.headerFilters);
  const sortedRows = sortRows(headerFilteredRows, columns, state.sort);
  const pagination = options.pagination || null;
  const totalFiltered = sortedRows.length;
  const totalPages = pagination ? Math.max(1, Math.ceil(totalFiltered / pagination.limit)) : 1;
  const safePage = pagination ? Math.min(Math.max(pagination.page, 1), totalPages) : 1;
  const pageStart = pagination ? (safePage - 1) * pagination.limit : 0;
  const pageEnd = pagination ? pageStart + pagination.limit : sortedRows.length;
  const visibleRows = sortedRows.slice(pageStart, pageEnd);
  const totalVisible = visibleRows.length;
  const empty = totalVisible === 0;
  const activeHeaderFiltersCount = getActiveHeaderFiltersCount(state.headerFilters);

  const filteredSums = buildSumMap(sortedRows, columns || []);
  const pageSums = buildSumMap(visibleRows, columns || []);
  const filteredSummary = buildSummaryText("Total filtrado", filteredSums);
  const pageSummary = buildSummaryText("Total da página", pageSums);

  if (APP_CONFIG.debugFinancialReconciliation) {
    const debugColumns = (columns || []).filter(isSummableColumn);
    const debugPayload = debugColumns.map((column) => {
      const rawFiltered = sortedRows.map((row) => resolveRawValue(row, column));
      const normalizedFiltered = rawFiltered.map((value) => parseNumericValue(value));
      const rawPage = visibleRows.map((row) => resolveRawValue(row, column));
      const normalizedPage = rawPage.map((value) => parseNumericValue(value));
      return {
        column: column.key,
        values: {
          brutoFiltrado: rawFiltered,
          normalizadoFiltrado: normalizedFiltered,
          brutoPaginado: rawPage,
          normalizadoPaginado: normalizedPage,
        },
        somas: {
          filtrado: filteredSums.find((item) => item.key === column.key)?.total || 0,
          pagina: pageSums.find((item) => item.key === column.key)?.total || 0,
        },
      };
    });

    console.log("[debugFinancialReconciliation] table", {
      title: options.title || "table",
      totalBruto: (rows || []).length,
      totalFiltrado: sortedRows.length,
      totalPagina: visibleRows.length,
      debugPayload,
    });
  }

  if (APP_CONFIG.debugFilters || APP_CONFIG.debugTotals) {
    const headerFiltersSnapshot = JSON.parse(JSON.stringify(state.headerFilters || {}));
    if (APP_CONFIG.debugFilters) {
      console.log("[debugFilters] filtros da tabela", {
        search: state.search || "",
        headerFilters: headerFiltersSnapshot,
      });
    }
    if (APP_CONFIG.debugTotals) {
      console.log("[debugTotals] totais da tabela", {
        totalBruto: (rows || []).length,
        totalFiltrado: totalFiltered,
        totalPaginado: visibleRows.length,
        somasFiltradas: filteredSums,
        somasPagina: pageSums,
      });
    }
  }

  const selectOptionsByColumn = {};
  columns.forEach((column) => {
    if (!column.filter || getFilterType(column) !== "select") return;
    const otherFilters = { ...state.headerFilters };
    delete otherFilters[column.key];
    const sourceRows = applyHeaderFilters(quickSearchRows, columns, otherFilters);
    selectOptionsByColumn[column.key] = buildSelectFilterOptions(sourceRows, column);
  });

  container.innerHTML = `
    ${buildToolbar(options, visibleRows, activeHeaderFiltersCount, totalFiltered, safePage, totalPages)}
    ${
      empty
        ? buildEmptyState(options)
        : `
          <div class="table-wrap">
            <table>
              <thead>
                <tr class="table-head-main">
                  ${columns
                    .map((column) => {
                      const sortable = column.sortable !== false;
                      const sortIndicator = getSortIndicator(state.sort, column.key);
                      const sortedClass = state.sort?.key === column.key ? " is-sorted" : "";
                      const activeFilterClass = getHeaderFilterValue(state, column.key)
                        ? " table-header-filter-active"
                        : "";
                      return `
                        <th class="${sortable ? "sortable" : ""}${sortedClass}${activeFilterClass}" data-key="${column.key}">
                          <span>${escapeHtml(column.label)}</span>
                          <span class="sort-indicator">${sortIndicator}</span>
                        </th>
                      `;
                    })
                    .join("")}
                </tr>
                <tr class="table-head-filters">
                  ${columns
                    .map((column) => {
                      const value = getHeaderFilterValue(state, column.key);
                      const optionsForColumn = selectOptionsByColumn[column.key] || [];
                      return buildHeaderFilterCell(column, value, optionsForColumn);
                    })
                    .join("")}
                </tr>
              </thead>
              <tbody>
                ${visibleRows
                  .map((row) => {
                    const cells = columns
                      .map((column) => {
                        const cell = resolveCellValue(row, column);
                        const rawValue = resolveRawValue(row, column);
                        const badgeClass = column.type === "status" ? renderBadge(rawValue) : "";
                        return `
                          <td class="${cell.className}">
                            <span class="${badgeClass}" title="${escapeHtml(cell.title)}">${escapeHtml(cell.value)}</span>
                          </td>
                        `;
                      })
                      .join("");
                    return `<tr>${cells}</tr>`;
                  })
                  .join("")}
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="${columns.length}">
                    <div class="table-summary">
                      ${filteredSummary ? `<div>${escapeHtml(filteredSummary)}</div>` : ""}
                      ${pageSummary ? `<div>${escapeHtml(pageSummary)}</div>` : ""}
                    </div>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
          ${pagination ? `<div class="pagination">${renderPaginationHtml(safePage, totalPages, totalFiltered)}</div>` : ""}
        `
    }
  `;

  const searchInput = container.querySelector("#tableSearch");
  if (searchInput) {
    const emitSearch = debounce(() => {
      options.onSearchChange?.(searchInput.value);
    }, 300);
    searchInput.addEventListener("input", emitSearch);
  }

  container.querySelectorAll("thead tr.table-head-main th.sortable").forEach((header) => {
    header.addEventListener("click", () => {
      const key = header.dataset.key;
      const nextSort = cycleSort(state.sort, key);
      if (options.onSortChange) {
        options.onSortChange(nextSort);
      } else {
        state.sort = nextSort;
        renderTable(container, columns, rows, options);
      }
    });
  });

  const emitHeaderFilter = debounce(() => {
    const nextHeaderFilters = {};
    container.querySelectorAll(".header-filter[data-filter-key]").forEach((input) => {
      const key = input.dataset.filterKey;
      if (input.tagName === "SELECT" && input.multiple) {
        const values = Array.from(input.selectedOptions)
          .map((option) => normalizeFilterValue(option.value))
          .filter((value) => !Array.isArray(value) && Boolean(value));
        if (values.includes("__ALL__")) {
          return;
        }
        if (values.length > 0) nextHeaderFilters[key] = values;
        return;
      }

      const value = normalizeFilterValue(input.value);
      if (Array.isArray(value)) {
        if (value.length > 0) nextHeaderFilters[key] = value;
      } else if (value) {
        nextHeaderFilters[key] = value;
      }
    });

    if (options.onHeaderFiltersChange) {
      options.onHeaderFiltersChange(nextHeaderFilters);
    } else {
      state.headerFilters = nextHeaderFilters;
      renderTable(container, columns, rows, options);
    }
  }, 200);

  container.querySelectorAll(".header-filter[data-filter-key]").forEach((input) => {
    input.addEventListener("input", emitHeaderFilter);
    input.addEventListener("change", emitHeaderFilter);
  });

  container.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.action;
      if (action === "csv") {
        const filename = options.exportName || "exportacao";
        downloadCsv(filename, columns, sortedRows);
      }
      if (action === "pdf") {
        openPdfPreview(options.title || "Relatório", columns, sortedRows, {
          description: options.pdfDescription || "Dados filtrados e ordenados da visão atual.",
          pdfNatureSummary: options.pdfNatureSummary,
        });
      }
      if (action === "clear") {
        options.onClearFilters?.();
      }
      if (action === "refresh") {
        options.onRefresh?.();
      }
      if (action === "clear-table-filters") {
        const clearSearch = options.clearTableFiltersAlsoSearch !== false;
        let handledExternally = false;

        if (options.onHeaderFiltersChange) {
          handledExternally = true;
          options.onHeaderFiltersChange({});
        } else {
          state.headerFilters = {};
        }

        if (clearSearch) {
          if (options.onSearchChange) {
            handledExternally = true;
            options.onSearchChange("");
          } else {
            state.search = "";
          }
        }

        if (!handledExternally) {
          renderTable(container, columns, rows, options);
        }
      }
    });
  });

  container.querySelectorAll("[data-page-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      const action = button.dataset.pageAction;
      if (action === "prev") {
        options.onPageChange?.(Math.max(1, (options.pagination?.page || 1) - 1));
      }
      if (action === "next") {
        const currentPage = options.pagination?.page || 1;
        const totalPagesForAction = options.pagination
          ? Math.max(1, Math.ceil(options.pagination.total / options.pagination.limit))
          : 1;
        options.onPageChange?.(Math.min(totalPagesForAction, currentPage + 1));
      }
    });
  });

  return {
    filteredRows: sortedRows,
    visibleRows,
    totalVisible,
  };
}

function renderPaginationHtml(page, totalPages, total) {
  return `
    <div class="pagination">
      <span class="small">Página ${page} de ${totalPages} | Total: ${total}</span>
      <button type="button" data-page-action="prev" ${page <= 1 ? "disabled" : ""}>Anterior</button>
      <button type="button" data-page-action="next" ${page >= totalPages ? "disabled" : ""}>Próxima</button>
    </div>
  `;
}
