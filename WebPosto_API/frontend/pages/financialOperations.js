import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";
import { buildFourQuestionBrief, enrichAlert } from "../services/executiveBrief.js";
import { countKpi } from "../services/executiveKpis.js";

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
  return value.replace("T", " ");
}

function renderScheduler(node, scheduler) {
  if (!node) return;
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card">
        <span>Status scheduler</span>
        <strong>${scheduler?.status || "—"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Última execução</span>
        <strong>${formatDateTime(scheduler?.lastRunAt)}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Próxima execução</span>
        <strong>${formatDateTime(scheduler?.nextRunAt)}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Intervalo</span>
        <strong>${scheduler?.intervalSeconds ? `${Math.round(scheduler.intervalSeconds / 3600)}h` : "—"}</strong>
      </article>
    </div>
  `;
}

function renderRecovery(node, recovery, circuit) {
  if (!node) return;
  node.innerHTML = `
    <div class="fin-ops-grid">
      <article class="card fin-ops-card">
        <span>Recovery</span>
        <strong>${recovery?.enabled ? "Ativo" : "Desabilitado"}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Pendentes</span>
        <strong>${recovery?.pendingCount ?? 0}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Recuperados</span>
        <strong>${recovery?.recoveredCount ?? 0}</strong>
      </article>
      <article class="card fin-ops-card">
        <span>Circuit financeiro</span>
        <strong>${circuitBadge(circuit?.status || recovery?.circuitStatus)}</strong>
      </article>
    </div>
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

function renderRetention(node, removed) {
  if (!node) return;
  const rows = Array.isArray(removed) ? removed : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Nenhum snapshot removido recentemente.</p>`;
    return;
  }
  node.innerHTML = `
    <ul class="fin-ops-alert-list">
      ${rows
        .map(
          (row) =>
            `<li>${row.file || row.snapshotType} · ${formatDateTime(row.removedAt)} · ${row.snapshotKey || "—"}</li>`
        )
        .join("")}
    </ul>
  `;
}

function renderExecutions(node, executions) {
  if (!node) return;
  const rows = Array.isArray(executions) ? executions : [];
  if (!rows.length) {
    node.innerHTML = `<p class="muted">Nenhuma execução registrada ainda.</p>`;
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
          <th>Duração</th>
          <th>Registros</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${rows
          .slice(0, 12)
          .map(
            (row) => `
          <tr>
            <td>${row.snapshot_type || "—"}</td>
            <td>${row.trigger_type || row.trigger || "—"}</td>
            <td>${row.source || "—"}</td>
            <td>${formatDateTime(row.started_at)}</td>
            <td>${row.duration_ms != null ? `${row.duration_ms} ms` : "—"}</td>
            <td>${row.record_count ?? row.records ?? "—"}</td>
            <td>${row.success === true ? "OK" : row.success === false ? "Falha" : "—"}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function mountFinancialOperationsDetail(node, data, filters) {
  const scheduler = data.scheduler || {};
  const recovery = data.recovery || {};
  const circuit = data.circuitBreaker || {};
  const alerts = data.alerts || [];
  const counts = data.alertCounts || {};
  const executions = data.executions || [];
  const retentionRemoved = data.retentionRemoved || [];

  node.innerHTML = `
    <p class="fin-monitor-meta muted">
      F08.2 — scheduler, recovery, retention e alertas preventivos.
      · Período: ${filters?.dataInicial || data.period?.dataInicial || "—"} →
      ${filters?.dataFinal || data.period?.dataFinal || "—"}
      · Retenção: ${data.retentionPolicyDays ?? 30} dias
      · Gerado em ${formatDateTime(data.generatedAt)}
    </p>
    <section class="card"><h3>Scheduler</h3><div id="finOpsScheduler"></div></section>
    <section class="card"><h3>Auto Recovery</h3><div id="finOpsRecovery"></div></section>
    <section class="card"><h3>Alertas ativos</h3><div id="finOpsAlerts"></div></section>
    <section class="card"><h3>Retention — removidos</h3><div id="finOpsRetention"></div></section>
    <section class="card"><h3>Audit trail (execuções)</h3><div id="finOpsExecutions"></div></section>
  `;

  renderScheduler(node.querySelector("#finOpsScheduler"), scheduler);
  renderRecovery(node.querySelector("#finOpsRecovery"), recovery, circuit);
  renderAlerts(node.querySelector("#finOpsAlerts"), alerts, counts);
  renderRetention(node.querySelector("#finOpsRetention"), retentionRemoved);
  renderExecutions(node.querySelector("#finOpsExecutions"), executions);
}

export function renderFinancialOperations(node, payload, filters, options = {}) {
  if (!node) return;
  const data = payload?.data || payload || {};
  const scheduler = data.scheduler || {};
  const recovery = data.recovery || {};
  const circuit = data.circuitBreaker || {};
  const counts = data.alertCounts || {};
  const criticalAlerts = counts.CRITICAL ?? 0;
  const pendingRecovery = recovery.pendingCount ?? 0;

  renderExecutiveCockpitPage(node, { cockpit: {}, executiveAnswers: {}, ...data }, filters, {
    title: "Operações Financeiras Autônomas",
    actionsHtml: `
      <button type="button" class="btn-secondary" id="finOpsRefresh">Atualizar</button>
      <button type="button" class="btn-secondary" id="finOpsRunNow">Executar agora</button>
    `,
    kpiOverrides: [
      { label: "Scheduler", value: String(scheduler.status || "—").slice(0, 10), trendPct: null, status: "ok" },
      { label: "Recovery", value: recovery.enabled ? "Ativo" : "Off", trendPct: null, status: pendingRecovery > 0 ? "warn" : "ok" },
      { label: "Alertas", value: String((counts.INFO ?? 0) + (counts.WARNING ?? 0) + criticalAlerts), trendPct: null, status: criticalAlerts > 0 ? "crit" : "ok" },
      { label: "Circuit", value: String(circuit.status || recovery.circuitStatus || "—").slice(0, 8), trendPct: null, status: circuit.status === "OPEN" ? "crit" : "ok" },
    ],
    brief: buildFourQuestionBrief({
      what: `Scheduler ${scheduler.status || "—"} · ${pendingRecovery} recovery pendente(s).`,
      why: criticalAlerts > 0 ? `${criticalAlerts} alerta(s) CRITICAL ativo(s).` : "Rotina autônoma operacional.",
      where: circuit.status === "OPEN" ? "Circuit financeiro aberto" : "Integração operacional",
      actionNow: criticalAlerts > 0 ? "Tratar alertas CRITICAL." : pendingRecovery > 0 ? "Acompanhar auto recovery." : "Executar ciclo manual se necessário.",
    }),
    alerts: (data.alerts || [])
      .filter((a) => a.severity === "CRITICAL")
      .slice(0, 3)
      .map((a) =>
        enrichAlert(
          { severity: "ALTO", title: a.code || "Alerta", detail: a.message || "", view: "financialOperations", origin: a.origin || "Admin" },
          { why: a.message || "", where: a.origin || "—", actionNow: "Investigar origem" }
        )
      ),
    detailBuilder: () => `<div id="finOpsDetailRoot"></div>`,
    detailSummary: "Scheduler, recovery e audit trail",
    refreshButtonId: "finOpsRefresh",
    defaultView: "financialOperations",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });

  node.querySelector("#finOpsRunNow")?.addEventListener("click", () => options.onRunNow?.());

  const detailRoot = node.querySelector("#finOpsDetailRoot");
  if (detailRoot) {
    mountFinancialOperationsDetail(detailRoot, data, filters);
  }
}
