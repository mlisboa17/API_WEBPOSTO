import { toSearchText } from "./formatters.js";

function parseDateValue(value) {
  if (!value) return null;
  const text = String(value).slice(0, 10);
  const parsed = Date.parse(text);
  return Number.isNaN(parsed) ? null : parsed;
}

function parseNumericValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(String(value).replace(",", "."));
  return Number.isNaN(number) ? null : number;
}

function getColumn(columns, key) {
  return columns.find((column) => column.key === key);
}

function getComparableValue(row, column) {
  const rawValue = column?.accessor ? column.accessor(row) : row?.[column.key];
  if (rawValue === null || rawValue === undefined || rawValue === "") return null;

  if (column?.type === "currency" || column?.type === "number") {
    return parseNumericValue(rawValue);
  }

  if (column?.type === "date") {
    return parseDateValue(rawValue);
  }

  return toSearchText(rawValue);
}

export function cycleSort(currentSort, key) {
  if (!currentSort || currentSort.key !== key) {
    return { key, direction: "asc" };
  }
  if (currentSort.direction === "asc") {
    return { key, direction: "desc" };
  }
  return null;
}

export function sortRows(rows, columns, sortState) {
  if (!sortState?.key) return rows.slice();
  const column = getColumn(columns, sortState.key);
  if (!column || column.sortable === false) return rows.slice();

  return rows
    .map((row, index) => ({ row, index }))
    .sort((left, right) => {
      const leftValue = getComparableValue(left.row, column);
      const rightValue = getComparableValue(right.row, column);

      if (leftValue === null && rightValue === null) return left.index - right.index;
      if (leftValue === null) return 1;
      if (rightValue === null) return -1;
      if (leftValue < rightValue) return sortState.direction === "asc" ? -1 : 1;
      if (leftValue > rightValue) return sortState.direction === "asc" ? 1 : -1;
      return left.index - right.index;
    })
    .map(({ row }) => row);
}

export function filterRows(rows, columns, searchValue) {
  const search = toSearchText(searchValue).trim();
  if (!search) return rows.slice();

  const searchableColumns = columns.filter((column) => column.searchable !== false);
  return rows.filter((row) =>
    searchableColumns.some((column) => {
      const rawValue = column.accessor ? column.accessor(row) : row?.[column.key];
      return toSearchText(rawValue).includes(search);
    })
  );
}

export function getSortIndicator(sortState, key) {
  if (!sortState || sortState.key !== key) return "";
  return sortState.direction === "asc" ? "↑" : "↓";
}
