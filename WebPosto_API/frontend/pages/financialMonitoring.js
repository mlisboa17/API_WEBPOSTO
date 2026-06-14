function healthBadge(status) {
  const key = String(status || "UNKNOWN").toLowerCase();
  return `<span class="fin-health-badge fin-health-badge--${key}">${status || "—"}</span>`;
}

function confidenceBadge(level) {
  const key = String(level || "MEDIA").toLowerCase();
  return `<span class="fin-confidence fin-confidence--${key}">${level || "—"}</span>`;
}

function formatAge(hours) {
  if (hours == null) return "—";
  const value = Number(hours);
  if (Number.isNaN(value)) return "—";
  if (value < 1) return `${Math.round(value * 60)} min`;
  if (value < 48) return `${value.toFixed(1)} h`;
  return `${(value / 24).toFixed(1)} d`;
}

function renderSummary(node, summary) {
  if (!summary) {
    node.innerHTML = `<p class="muted">Nenhum assessment disponível para o período.</p>`;
    return;
  }
  node.innerHTML = `
    <div class="fin-monitor-summary">
      <article class="card fin-monitor-card">
        <span>Status geral</span>
        <strong>${healthBadge(summary.overallStatus)}</strong>
      </article>
      <article class="card fin-monitor-card">
        <span>Snapshots no período</span>
        <strong>${summary.totalSnapshots ?? 0}/${summary.expectedSnapshots ?? 4}</strong>
      </article>
      <article class="card fin-monitor-card fin-monitor-card--healthy">
        <span>Saudáveis</span>
        <strong>${summary.healthy ?? 0}</strong>
      </article>
      <article class="card fin-monitor-card fin-monitor-card--warning">
        <span>Warning</span>
        <strong>${summary.warning ?? 0}</strong>
      </article>
      <article class="card fin-monitor-card fin-monitor-card--critical">
        <span>Críticos</span>
        <strong>${summary.critical ?? 0}</strong>
      </article>
      <article class="card fin-monitor-card">
        <span>Score médio</span>
        <strong>${summary.averageHealthScore ?? "—"}</strong>
      </article>
      <article class="card fin-monitor-card">
        <span>Cobertura</span>
        <strong>${summary.coverageComplete ? "Completa" : "Lacunas"}</strong>
      </article>
    </div>
    ${
      summary.coverageGaps?.length
        ? `<p class="fin-monitor-gaps"><strong>Lacunas:</strong> ${summary.coverageGaps.join(", ")}</p>`
        : ""
    }
  `;
}

function renderSnapshotsTable(node, snapshots) {
  const rows = Array.isArray(snapshots) ? snapshots : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Sem snapshots classificados para o período.</p>`;
    return;
  }
  node.innerHTML = `
    <table class="data-table fin-monitor-table">
      <thead>
        <tr>
          <th>Snapshot</th>
          <th>Status</th>
          <th>Idade</th>
          <th>Confiança</th>
          <th>Origem</th>
          <th>Última atualização</th>
          <th>Registros</th>
          <th>Lineage</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
          <tr>
            <td>${row.label || row.snapshotType || "—"}</td>
            <td>${healthBadge(row.healthStatus)}</td>
            <td>${formatAge(row.snapshotAgeHours)}</td>
            <td>${confidenceBadge(row.confidenceLevel)}</td>
            <td>${row.source || "—"}</td>
            <td>${row.lastUpdated || "—"}</td>
            <td>${row.recordCount ?? "—"}</td>
            <td>${row.lineagePresent ? "Sim" : "Não"}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderInventoryTable(node, inventory) {
  const rows = Array.isArray(inventory) ? inventory : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Inventário vazio — nenhum arquivo em snapshots/financial/.</p>`;
    return;
  }
  node.innerHTML = `
    <details class="fin-monitor-inventory" open>
      <summary>Inventário global (${rows.length} arquivos)</summary>
      <table class="data-table fin-monitor-table">
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Chave</th>
            <th>Status</th>
            <th>Idade</th>
            <th>Confiança</th>
            <th>Origem</th>
            <th>Tamanho</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (row) => `
            <tr>
              <td>${row.label || row.snapshotType}</td>
              <td>${row.snapshotKey || "—"}</td>
              <td>${healthBadge(row.healthStatus)}</td>
              <td>${formatAge(row.snapshotAgeHours)}</td>
              <td>${confidenceBadge(row.confidenceLevel)}</td>
              <td>${row.source || "—"}</td>
              <td>${row.sizeBytes ? `${Math.round(row.sizeBytes / 1024)} KB` : "—"}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </details>
  `;
}

export function renderFinancialMonitoring(node, payload, filters, options = {}) {
  if (!node) return;
  const data = payload?.data || payload || {};
  const assessment = data.assessment || {};
  const summary = assessment.summary || null;
  const snapshots = assessment.snapshots || [];
  const inventory = data.inventory || [];
  const generatedAt = data.generatedAt || new Date().toISOString();

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Monitoramento de Snapshots Financeiros</h2>
        <p class="muted">F08.1 — saúde, freshness, cobertura e confiança (sem WebPosto live).</p>
      </div>
      <button type="button" class="btn-secondary" id="finMonitorRefresh">Atualizar</button>
    </header>
    <p class="fin-monitor-meta muted">
      Período: ${filters?.dataInicial || "—"} → ${filters?.dataFinal || "—"}
      · Gerado em ${generatedAt}
    </p>
    <section id="finMonitorSummary"></section>
    <section class="card">
      <h3>Snapshots do período</h3>
      <div id="finMonitorSnapshots"></div>
    </section>
    <section class="card">
      <div id="finMonitorInventory"></div>
    </section>
  `;

  renderSummary(node.querySelector("#finMonitorSummary"), summary);
  renderSnapshotsTable(node.querySelector("#finMonitorSnapshots"), snapshots);
  renderInventoryTable(node.querySelector("#finMonitorInventory"), inventory);

  const refreshBtn = node.querySelector("#finMonitorRefresh");
  if (refreshBtn && typeof options.onRefresh === "function") {
    refreshBtn.addEventListener("click", () => options.onRefresh());
  }
}
