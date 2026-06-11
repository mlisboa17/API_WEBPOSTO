import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function opLabel(item) {
  if (!item) return "—";
  const name = item.employeeName || item.employeeName;
  const code = item.funcionarioCodigo;
  return name ? `${name} (${code})` : String(code ?? "—");
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
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
  return `
    <section class="panel">
      <h3>${title}</h3>
      <table class="data-table">
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </section>`;
}

export function renderManagementAction(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Management Action Center…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const qa = payload.qa || {};
  const parecer = payload.parecerFinal || "";

  const actionCols = [
    { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
    { key: "primaryAction", label: "Ação Principal" },
    { key: "globalScore", label: "Score" },
    { key: "riskScore", label: "Risco" },
  ];

  const promoCols = [
    { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
    { key: "motivo", label: "Motivo" },
    { key: "globalScore", label: "Score" },
    { key: "roiNorm", label: "ROI" },
  ];

  const bonusCols = [
    { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
    { key: "bonusRecomendado", label: "Bônus", money: true },
    { key: "bonusRoiEsperado", label: "ROI Esperado" },
  ];

  const trainCols = [
    { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
    {
      key: "categories",
      label: "Categorias",
      render: (r) => (r.categories || []).join(", ") || "—",
    },
  ];

  const pdvCols = [
    { key: "pdvCodigo", label: "PDV" },
    { key: "receitaBruta", label: "Receita", money: true },
    { key: "destruicaoMargem", label: "Destruição", money: true },
    { key: "roi", label: "ROI" },
  ];

  const turnCols = [
    { key: "turno", label: "Turno" },
    { key: "receitaBruta", label: "Receita", money: true },
    { key: "shiftRiskScore", label: "Risco" },
  ];

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Management Action Center</h2>
        <p class="muted">F04.4 — Governança & Ações Gerenciais · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="macRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="macExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Promoções</span><strong>${exec["1_elegiveisPromocao"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Bonificações</span><strong>${exec["2_elegiveisBonus"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Treinamentos</span><strong>${exec["3_precisamTreinamento"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Auditorias</span><strong>${exec["4_precisamAuditoria"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Ações Geradas</span><strong>${exec["12_acoesAutomaticasGeradas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Evidência QA</span><strong>${qa.evidenciaCompleta ? "100%" : "Pendente"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Impacto Financeiro</span><strong>${fmtMoney(exec["14_impactoFinanceiroEsperado"])}</strong></article>
    </div>
    ${renderTable("Ações Pendentes", cockpit.acoesPendentes, actionCols)}
    ${renderTable("Promoções", cockpit.promocoes, promoCols)}
    ${renderTable("Bonificações", cockpit.bonificacoes, bonusCols)}
    ${renderTable("Treinamentos", cockpit.treinamentos, trainCols)}
    ${renderTable("Auditorias", cockpit.auditorias, actionCols)}
    ${renderTable("PDVs Críticos", cockpit.pdvsCriticos, pdvCols)}
    ${renderTable("Turnos Críticos", cockpit.turnosCriticos, turnCols)}`;

  node.querySelector("#macRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#macExport")?.addEventListener("click", () => {
    downloadCsv(cockpit.acoesPendentes || [], `management_action_${filters?.dataInicial}_${filters?.dataFinal}`);
  });
}
