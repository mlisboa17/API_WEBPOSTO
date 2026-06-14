import { renderExpenses } from "./expenses.js";
import { renderFinancialResilienceBanner } from "../components/financialResilienceBanner.js";

export function renderFinancialExpenses(container, payload, onPageChange, options = {}) {
  if (!container) return;
  const data = payload?.data ?? payload;
  const resilience = payload?.resilience ?? options.resilience;

  container.innerHTML = "";
  renderFinancialResilienceBanner(container, resilience);
  const body = document.createElement("div");
  container.appendChild(body);

  if (!data?.data?.length && resilience?.source === "degraded") {
    body.innerHTML = `<p class="muted">${resilience?.banner || "Despesas indisponíveis no momento."}</p>`;
    return;
  }

  renderExpenses(body, data, onPageChange, options);
}
