import { renderDashboard } from "./dashboard.js";

export function renderFinancialOverview(container, payload, options = {}) {
  if (!container) return;
  const overview = payload?.data ?? payload;
  const resilience = payload?.resilience;

  container.innerHTML = "";

  if (!overview) {
    container.innerHTML = `<p class="muted">Dados financeiros indisponíveis no momento.</p>`;
    return;
  }

  const postos = overview?.postos || [];
  if (resilience?.source === "degraded" && postos.length === 0) {
    const hint =
      resilience?.banner ||
      "Sem dados consolidados para este período. Tente outro intervalo ou clique em Atualizar.";
    container.innerHTML = `<p class="muted">${hint}</p>`;
    return;
  }

  renderDashboard(container, overview, { ...options, resilience });
}