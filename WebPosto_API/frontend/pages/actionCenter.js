import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .filter(Boolean)
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          if (c.money) return `<td>${fmtMoney(val)}</td>`;
          return `<td>${val ?? "—"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderActionCenter(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Action Center…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const tracking = cockpit.tracking || {};
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Action Center</h2>
        <p class="muted">F05.2 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="actionCenterRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="actionCenterExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Total Ações</span><strong>${exec["1_totalAcoes"] ?? cockpit.totalAcoes ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Dono Nominal</span><strong>${exec["2_donoNominal"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Validadas</span><strong>${tracking.validadas ?? exec["6_validadas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Esperado</span><strong>${fmtMoney(cockpit.roiEsperadoTotal)}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Realizado</span><strong>${fmtMoney(cockpit.roiRealizadoTotal)}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Δ ROI</span><strong>${fmtMoney(cockpit.roiDeltaTotal)}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Sem Evidência</span><strong>${(cockpit.semEvidencia || []).length}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Auditável</span><strong>${exec["18_auditavel"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Prioridade 1", cockpit.prioridade1, [
      { key: "lifecycleStatus", label: "Status" },
      { key: "acao", label: "Ação" },
      { key: "ownerName", label: "Responsável" },
      { key: "roiEsperado", label: "ROI Esp.", money: true },
      { key: "decisionEvidenceType", label: "Evidência" },
    ])}
    ${renderTable("Escalonadas / Vencidas", cockpit.vencidas, [
      { key: "acao", label: "Ação" },
      { key: "ownerName", label: "Responsável" },
      { key: "lifecycleStatus", label: "Status" },
      { key: "escalationReasons", label: "Motivos", render: (r) => (r.escalationReasons || []).join(", ") },
    ])}
    ${renderTable("Ações por Responsável", cockpit.acoesPorResponsavel, [
      { key: "ownerName", label: "Responsável" },
      { key: "total", label: "Ações" },
    ])}
  `;

  node.querySelector("#actionCenterRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#actionCenterExport")?.addEventListener("click", () => {
    downloadCsv("action-center.csv", cockpit.prioridade1 || []);
  });
}
