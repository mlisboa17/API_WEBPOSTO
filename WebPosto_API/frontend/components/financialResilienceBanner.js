function formatAgeHours(hours) {
  if (hours == null || Number.isNaN(Number(hours))) return "—";
  const value = Number(hours);
  if (value < 1) return `${Math.round(value * 60)} min`;
  return `${value.toFixed(1)} h`;
}

export function renderFinancialResilienceBanner(container, resilience) {
  if (!resilience) return;
  const existing = container.querySelector(".fin-resilience-banner");
  if (existing) existing.remove();

  const source = resilience.source || "unknown";
  const health = resilience.health || {};
  const healthStatus =
    resilience.healthStatus || health.healthStatus || (source === "live" ? "HEALTHY" : null);
  const confidence =
    resilience.confidenceLevel || health.confidenceLevel || (source === "live" ? "ALTA" : "—");
  const origin = resilience.dataOrigin || health.source || source;
  const age = resilience.snapshotAgeHours ?? health.snapshotAgeHours;
  const lastUpdated = resilience.lastUpdated || health.lastUpdated;
  const title =
    resilience.banner ||
    (source === "live" ? "Dados em tempo real (WebPosto)" : "Governança de snapshot financeiro");

  const banner = document.createElement("div");
  banner.className = `fin-resilience-banner fin-resilience-banner--${source} fin-health-status--${String(
    healthStatus || "unknown"
  ).toLowerCase()}`;
  banner.innerHTML = `
    <strong>${title}</strong>
    <div class="fin-health-meta">
      <span>Origem: <strong>${origin}</strong></span>
      ${lastUpdated ? `<span>Última atualização: ${lastUpdated}</span>` : ""}
      ${age != null ? `<span>Idade do snapshot: ${formatAgeHours(age)}</span>` : ""}
      ${
        healthStatus
          ? `<span>Saúde: <span class="fin-health-badge fin-health-badge--${String(
              healthStatus
            ).toLowerCase()}">${healthStatus}</span></span>`
          : ""
      }
      ${confidence ? `<span>Confiança: <strong>${confidence}</strong></span>` : ""}
      ${resilience.circuitStatus ? `<span>Circuit: ${resilience.circuitStatus}</span>` : ""}
    </div>
  `;
  container.prepend(banner);
}
