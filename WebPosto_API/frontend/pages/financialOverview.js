import { renderDashboard } from "./dashboard.js";
import { renderFinancialResilienceBanner } from "../components/financialResilienceBanner.js";

export function renderFinancialOverview(container, payload, options = {}) {
  if (!container) return;
  const overview = payload?.data ?? payload;
  const resilience = payload?.resilience ?? options.resilience;

  container.innerHTML = "";
  renderFinancialResilienceBanner(container, resilience);
  const body = document.createElement("div");
  container.appendChild(body);

  if (!overview || (resilience?.source === "degraded" && !overview?.postos?.length)) {
    body.innerHTML = `<p class="muted">${resilience?.banner || "Dados financeiros indisponíveis no momento."}</p>`;
    return;
  }

  renderDashboard(body, overview, options);
}
