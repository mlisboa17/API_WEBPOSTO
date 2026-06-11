import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function bandClass(band) {
  const map = {
    EXCELENTE: "badge-success",
    BOM: "badge-muted",
    ATENÇÃO: "badge-warning",
    CRÍTICO: "badge-danger",
  };
  return map[band] || "badge-muted";
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = item[c.key];
          if (c.band) return `<td><span class="badge ${bandClass(val)}">${val ?? "—"}</span></td>`;
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

export function renderOperationRoi(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Operation ROI…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const parecer = payload.parecerFinal || "";

  const pdvCols = [
    { key: "pdvCodigo", label: "PDV" },
    { key: "receitaBruta", label: "Receita", money: true },
    { key: "resultadoLiquido", label: "Resultado", money: true },
    { key: "roi", label: "ROI" },
    { key: "destruicaoMargem", label: "Destruição", money: true },
  ];

  const turnCols = [
    { key: "turno", label: "Turno" },
    { key: "receitaBruta", label: "Receita", money: true },
    { key: "resultadoLiquido", label: "Resultado", money: true },
    { key: "roi", label: "ROI" },
    { key: "shiftRiskScore", label: "Risco Turno" },
  ];

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Operation ROI</h2>
        <p class="muted">F04.3 — Store & Shift Profitability · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="opRoiRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="opRoiExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Lucro Top 5 PDVs</span><strong>${fmtMoney(exec["17_lucroTop5Pdvs"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Risco PDVs Críticos</span><strong>${fmtMoney(exec["18_riscoPdvsCriticos"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Decisões Automáticas</span><strong>${exec["19_decisoesOperacionaisAutomaticas"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top PDVs", cockpit.topPdvs, pdvCols)}
    ${renderTable("Top Turnos", cockpit.topTurnos, turnCols)}
    ${renderTable("Top Operadores", cockpit.topOperadores, [
      { key: "employeeName", label: "Operador" },
      { key: "receitaBruta", label: "Receita", money: true },
      { key: "resultadoLiquido", label: "Resultado", money: true },
      { key: "profitabilityScore", label: "Score" },
      { key: "profitabilityBand", label: "Banda", band: true },
    ])}
    ${renderTable("PDVs Críticos", cockpit.pdvsCriticos, pdvCols)}
    ${renderTable("Turnos Críticos", cockpit.turnosCriticos, turnCols)}
    ${renderTable("ROI Operacional (PDV + Turno)", cockpit.roiOperacional, [
      { key: "pdvCodigo", label: "PDV" },
      { key: "turno", label: "Turno" },
      { key: "resultadoLiquido", label: "Resultado", money: true },
      { key: "roi", label: "ROI" },
    ])}`;

  node.querySelector("#opRoiRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#opRoiExport")?.addEventListener("click", () => {
    downloadCsv(cockpit.topPdvs || [], `operation_roi_${filters?.dataInicial}_${filters?.dataFinal}`);
  });
}
