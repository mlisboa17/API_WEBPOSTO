import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function bandClass(band) {
  const map = {
    GERA_LUCRO: "badge-success",
    NEUTRO: "badge-muted",
    DESTRUI_MARGEM: "badge-danger",
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

export function renderPeopleRoi(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando People ROI…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const parecer = payload.parecerFinal || "";

  const cols = [
    { key: "employeeName", label: "Operador" },
    { key: "receitaBruta", label: "Receita", money: true },
    { key: "resultadoLiquido", label: "Resultado", money: true },
    { key: "roi", label: "ROI" },
    { key: "profitabilityScore", label: "Profit Score" },
    { key: "profitabilityBand", label: "Banda", band: true },
  ];

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>People ROI</h2>
        <p class="muted">F04.2 — Profitability & Management Decision · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="roiRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="roiExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Lucro Top 10</span><strong>${fmtMoney(exec["13_lucroTop10"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Risco Críticos</span><strong>${fmtMoney(exec["14_riscoCriticos"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Meritocracia</span><strong>${exec["18_gestaoMeritocratica"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top ROI", cockpit.topRoi, cols)}
    ${renderTable("Top Lucro", cockpit.topLucro, cols)}
    ${renderTable("Top Risco Econômico", cockpit.topRisco, [
      { key: "employeeName", label: "Operador" },
      { key: "destruicaoMargem", label: "Destruição", money: true },
      { key: "descontos", label: "Descontos", money: true },
      { key: "faltas", label: "Faltas", money: true },
    ])}
    ${renderTable("Top Bônus (ROI)", cockpit.topBonus, [
      { key: "employeeName", label: "Operador" },
      { key: "bonusRoi", label: "Bonus ROI" },
      { key: "bonusCustoEstimado", label: "Custo Est.", money: true },
      { key: "resultadoLiquido", label: "Resultado", money: true },
    ])}
    ${renderTable("Top Auditoria", cockpit.topAuditoria, [
      { key: "employeeName", label: "Operador" },
      { key: "primaryAction", label: "Ação" },
      { key: "profitabilityBand", label: "Banda", band: true },
      { key: "resultadoLiquido", label: "Resultado", money: true },
    ])}`;

  node.querySelector("#roiRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#roiExport")?.addEventListener("click", () => {
    downloadCsv(cockpit.topRoi || [], `people_roi_${filters?.dataInicial}_${filters?.dataFinal}`);
  });
}
