function healthClass(classification) {
  const key = String(classification || "ATENÇÃO").toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
  return `fin-ops-health fin-ops-health--${key}`;
}

function alertBadge(severity) {
  const key = String(severity || "INFO").toLowerCase();
  return `<span class="fin-alert fin-alert--${key}">${severity}</span>`;
}

function circuitBadge(status) {
  const key = String(status || "CLOSED").toLowerCase().replace("_", "-");
  return `<span class="circuit-badge circuit-badge--${key}">${status || "—"}</span>`;
}

function formatDateTime(value) {
  if (!value) return "—";
  return String(value).replace("T", " ");
}

function timelineIcon(eventType) {
  const map = {
    SNAPSHOT_GENERATED: "📸",
    SNAPSHOT_FAILED: "⚠️",
    RECOVERY_TRIGGERED: "🔄",
    RECOVERY_SUCCEEDED: "✅",
    CIRCUIT_OPEN: "🔴",
    CIRCUIT_CLOSED: "🟢",
    RETENTION_APPLIED: "🗑️",
    HEALTH_WARNING: "⚠️",
    HEALTH_CRITICAL: "🚨",
    SCHEDULER_RUN: "⏱️",
  };
  return map[eventType] || "•";
}

function renderExecutiveCards(node, cards, health) {
  if (!node) return;
  const coverage = cards?.snapshotCoverage || {};
  const alerts = cards?.activeAlerts || {};
  node.innerHTML = `
    <div class="fin-ops-center-hero card">
      <div class="${healthClass(health?.classification)}">
        <span>Financial Health Score</span>
        <strong class="fin-ops-score">${health?.score ?? "—"}</strong>
        <em>${health?.classification || "—"}</em>
      </div>
      <ul class="fin-ops-score-breakdown">
        <li>Snapshot ${health?.components?.snapshotHealth ?? "—"}</li>
        <li>Scheduler ${health?.components?.scheduler ?? "—"}</li>
        <li>Recovery ${health?.components?.recovery ?? "—"}</li>
        <li>Alertas ${health?.components?.alerts ?? "—"}</li>
        <li>Circuits ${health?.components?.circuits ?? "—"}</li>
      </ul>
    </div>
    <div class="fin-ops-grid fin-ops-grid--cards">
      <article class="card fin-ops-card">
        <span>Snapshot Coverage</span>
        <strong>${coverage.complete ? "Completa" : "Lacunas"}</strong>
        <small>${coverage.total ?? 0}/${coverage.expected ?? 4}</small>
      </article>
      <article class="card fin-ops-card">
        <span>Recovery Status</span>
        <strong>${cards?.recoveryStatus?.pendingCount ? `${cards.recoveryStatus.pendingCount} pendente(s)` : "OK"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Scheduler Status</span>
        <strong>${cards?.schedulerStatus?.status || "—"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Alertas Ativos</span>
        <strong>${(alerts.CRITICAL || 0) + (alerts.WARNING || 0) + (alerts.INFO || 0)}</strong>
        <small>C:${alerts.CRITICAL || 0} W:${alerts.WARNING || 0}</small>
      </article>
      <article class="card fin-ops-card">
        <span>Última Execução</span>
        <strong>${formatDateTime(cards?.lastExecution)}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Próxima Execução</span>
        <strong>${formatDateTime(cards?.nextExecution)}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Circuit Status</span>
        <strong>${circuitBadge(cards?.circuitStatus)}</strong>
      </article>
    </div>
  `;
}

function renderOperationalStatus(node, data) {
  if (!node) return;
  const scheduler = data.scheduler || {};
  const recovery = data.recovery || {};
  const circuit = data.circuitBreakers || {};
  const retention = data.retention || {};
  const health = data.snapshotHealth?.assessment?.summary || {};
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card">
        <span>Scheduler</span>
        <strong>${scheduler.status || "—"}</strong>
        <small>Próximo: ${formatDateTime(scheduler.nextRunAt)}</small>
      </article>
      <article class="card fin-ops-card">
        <span>Recovery</span>
        <strong>${recovery.enabled ? "Ativo" : "Off"} · ${recovery.pendingCount ?? 0} pend.</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Snapshot Health</span>
        <strong>${health.overallStatus || "—"} · score ${health.averageHealthScore ?? "—"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Retention</span>
        <strong>${retention.policyDays ?? 30}d · ${retention.expiredCandidates ?? 0} candidatos</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Circuit Breaker</span>
        <strong>${circuitBadge(circuit.status)}</strong>
        <small>${circuit.financialEndpoint || "—"}</small>
      </article>
    </div>
  `;
}

function renderTimeline(node, events) {
  if (!node) return;
  const rows = Array.isArray(events) ? events : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Nenhum evento operacional registrado.</p>`;
    return;
  }
  node.innerHTML = `
    <ol class="fin-ops-timeline">
      ${rows
        .map(
          (ev) => `
        <li class="fin-ops-timeline-item fin-ops-timeline-item--${String(ev.severity || "INFO").toLowerCase()}">
          <span class="fin-ops-timeline-icon">${timelineIcon(ev.eventType)}</span>
          <div>
            <strong>${ev.label || ev.eventType}</strong>
            <span class="muted">${formatDateTime(ev.timestamp)} · ${ev.eventType}</span>
            <p>${ev.detail || "—"}${ev.origin ? ` <span class="muted">(${ev.origin})</span>` : ""}</p>
          </div>
        </li>`
        )
        .join("")}
    </ol>
  `;
}

function renderAlerts(node, alerts, counts) {
  if (!node) return;
  const rows = Array.isArray(alerts) ? alerts : [];
  node.innerHTML = `
    <div class="fin-ops-alert-counts">
      <span>INFO: ${counts?.INFO ?? 0}</span>
      <span>WARNING: ${counts?.WARNING ?? 0}</span>
      <span>CRITICAL: ${counts?.CRITICAL ?? 0}</span>
    </div>
    ${
      rows.length
        ? `<ul class="fin-ops-alert-list">
            ${rows
              .map(
                (alert) =>
                  `<li>${alertBadge(alert.severity)} <strong>${alert.code}</strong> — ${alert.message} <span class="muted">(${alert.origin || "—"})</span></li>`
              )
              .join("")}
          </ul>`
        : `<p class="muted">Nenhum alerta ativo.</p>`
    }
  `;
}

function renderExecutions(node, executions) {
  if (!node) return;
  const rows = Array.isArray(executions) ? executions : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Nenhuma execução registrada.</p>`;
    return;
  }
  node.innerHTML = `
    <table class="data-table fin-monitor-table">
      <thead>
        <tr>
          <th>Tipo</th>
          <th>Trigger</th>
          <th>Origem</th>
          <th>Início</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .slice(0, 15)
          .map(
            (row) => `
          <tr>
            <td>${row.snapshot_type || "—"}</td>
            <td>${row.trigger_type || row.trigger || "—"}</td>
            <td>${row.source || "—"}</td>
            <td>${formatDateTime(row.started_at)}</td>
            <td>${row.success === true ? "OK" : row.success === false ? "Falha" : "—"}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
}

export function renderFinancialOperationsCenter(node, payload, filters, options = {}) {
  if (!node) return;
  const data = payload?.data || payload || {};
  const cards = data.cards || {};
  const health = data.executiveHealthScore || cards.financialHealthScore || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Financial Operations Center</h2>
        <p class="muted">F08.3 — cockpit unificado: health, scheduler, recovery, circuits, alertas e timeline.</p>
      </div>
      <div class="fin-ops-actions">
        <button type="button" class="btn-secondary" id="finOpsCenterRefresh">Atualizar</button>
      </div>
    </header>
    <p class="fin-monitor-meta muted">
      Período: ${filters?.dataInicial || data.period?.dataInicial || "—"} →
      ${filters?.dataFinal || data.period?.dataFinal || "—"}
      · Snapshot-first · Live opcional
      · Gerado em ${formatDateTime(data.generatedAt)}
    </p>

    <section class="fin-ops-center-section">
      <h3>1. Visão Executiva</h3>
      <div id="finOpsCenterExecutive"></div>
    </section>

    <section class="fin-ops-center-section card">
      <h3>2. Status Operacional</h3>
      <div id="finOpsCenterStatus"></div>
    </section>

    <section class="fin-ops-center-section card">
      <h3>3. Timeline &amp; Detalhes</h3>
      <h4>Timeline Operacional</h4>
      <div id="finOpsCenterTimeline"></div>
      <h4>Alertas</h4>
      <div id="finOpsCenterAlerts"></div>
      <h4>Execuções</h4>
      <div id="finOpsCenterExecutions"></div>
    </section>
  `;

  renderExecutiveCards(node.querySelector("#finOpsCenterExecutive"), cards, health);
  renderOperationalStatus(node.querySelector("#finOpsCenterStatus"), data);
  renderTimeline(node.querySelector("#finOpsCenterTimeline"), data.timeline);
  renderAlerts(node.querySelector("#finOpsCenterAlerts"), data.alerts, data.alertCounts);
  renderExecutions(node.querySelector("#finOpsCenterExecutions"), data.executions);

  node.querySelector("#finOpsCenterRefresh")?.addEventListener("click", () => options.onRefresh?.());
}
