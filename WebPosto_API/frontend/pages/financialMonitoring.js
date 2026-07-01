import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";
import { buildFourQuestionBrief, enrichAlert } from "../services/executiveBrief.js";
import { countKpi } from "../services/executiveKpis.js";

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

function mountFinancialMonitoringDetail(node, data, filters, generatedAt) {
  const assessment = data.assessment || {};
  const summary = assessment.summary || null;
  const snapshots = assessment.snapshots || [];
  const inventory = data.inventory || [];

  node.innerHTML = `
    <p class="fin-monitor-meta muted">
      F08.1 — saúde, freshness, cobertura e confiança (sem WebPosto live).
      · Período: ${filters?.dataInicial || "—"} → ${filters?.dataFinal || "—"}
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
}

export function renderFinancialMonitoring(node, payload, filters, options = {}) {
  if (!node) return;
  const data = payload?.data || payload || {};
  const assessment = data.assessment || {};
  const summary = assessment.summary || {};
  const generatedAt = data.generatedAt || new Date().toISOString();
  const critical = summary.critical ?? 0;
  const healthy = summary.healthy ?? 0;

  renderExecutiveCockpitPage(node, { cockpit: {}, executiveAnswers: {}, ...data }, filters, {
    title: "Monitoramento de Snapshots",
    actionsHtml: `<button type="button" class="btn-secondary" id="finMonitorRefresh">Atualizar</button>`,
    kpiOverrides: [
      { label: "Status", value: String(summary.overallStatus || "—").slice(0, 10), trendPct: null, status: critical > 0 ? "crit" : "ok" },
      {
        label: "Snapshots",
        value: `${summary.totalSnapshots ?? 0}/${summary.expectedSnapshots ?? 4}`,
        trendPct: null,
        status: summary.coverageComplete ? "ok" : "warn",
      },
      { label: "Saudáveis", value: countKpi(healthy), trendPct: null, status: "ok" },
      { label: "Críticos", value: countKpi(critical), trendPct: null, status: critical > 0 ? "crit" : "ok" },
    ],
    brief: buildFourQuestionBrief({
      what: `Saúde ${summary.overallStatus || "—"} · score médio ${summary.averageHealthScore ?? "—"}.`,
      why:
        critical > 0
          ? `${critical} snapshot(s) crítico(s) no período.`
          : summary.coverageGaps?.length
            ? `Lacunas: ${summary.coverageGaps.join(", ")}.`
            : "Cobertura e freshness dentro do esperado.",
      where: summary.coverageComplete ? "Cobertura completa" : "Lacunas de cobertura",
      actionNow: critical > 0 ? "Investigar snapshots críticos hoje." : "Validar inventário global.",
    }),
    alerts: (assessment.snapshots || [])
      .filter((s) => String(s.healthStatus || "").toUpperCase().includes("CRIT"))
      .slice(0, 3)
      .map((s) =>
        enrichAlert(
          {
            severity: "ALTO",
            title: s.label || s.snapshotType || "Snapshot crítico",
            detail: formatAge(s.snapshotAgeHours),
            view: "financialMonitoring",
            origin: "Admin",
          },
          { why: s.healthStatus || "Status crítico", where: s.source || "—", actionNow: "Regenerar snapshot" }
        )
      ),
    detailBuilder: () => `<div id="finMonitorDetailRoot"></div>`,
    detailSummary: "Inventário técnico e lineage",
    refreshButtonId: "finMonitorRefresh",
    defaultView: "financialMonitoring",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });

  const detailRoot = node.querySelector("#finMonitorDetailRoot");
  if (detailRoot) {
    mountFinancialMonitoringDetail(detailRoot, data, filters, generatedAt);
  }
}
