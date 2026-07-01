import { renderExpenses } from "./expenses.js";

export function renderFinancialExpenses(container, payload, onPageChange, options = {}) {
  if (!container) return;
  const data = payload?.data ?? payload;

  container.innerHTML = "";

  if (!data?.data?.length && payload?.resilience?.source === "degraded") {
    container.innerHTML = `<p class="muted">Despesas indisponíveis no momento.</p>`;
    return;
  }

  renderExpenses(container, data, onPageChange, { ...options, filters: options.filters });
}