export function createTableState(initial = {}) {
  return {
    search: initial.search || "",
    sort: initial.sort || null,
    headerFilters: initial.headerFilters || {},
  };
}
