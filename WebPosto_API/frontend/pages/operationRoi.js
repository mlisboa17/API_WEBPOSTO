import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";
import { buildFourQuestionBrief } from "../services/executiveBrief.js";
import { moneyKpi } from "../services/executiveKpis.js";

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

  const cockpit = payload?.cockpit || {};
  const exec = payload?.executiveAnswers || {};
  const parecer = payload?.parecerFinal || "";

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

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Operation ROI",
    actionsHtml: `
      <button type="button" id="opRoiRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="opRoiExport" class="btn-secondary">Exportar CSV</button>
    `,
    kpiOverrides: [
      { label: "Lucro Top 5", value: moneyKpi(exec["17_lucroTop5Pdvs"]), trendPct: null, status: "ok" },
      { label: "Risco PDVs", value: moneyKpi(exec["18_riscoPdvsCriticos"]), trendPct: null, status: "crit" },
      { label: "Paridade Δ", value: String(exec.paridadeDelta ?? "—"), trendPct: null, status: "ok" },
      {
        label: "Decisões Auto",
        value: exec["19_decisoesOperacionaisAutomaticas"] ? "Sim" : "Não",
        trendPct: null,
        status: exec["19_decisoesOperacionaisAutomaticas"] ? "ok" : "warn",
      },
    ],
    brief: buildFourQuestionBrief({
      what: `Lucro top 5 PDVs ${moneyKpi(exec["17_lucroTop5Pdvs"])} · risco ${moneyKpi(exec["18_riscoPdvsCriticos"])}.`,
      why: parecer ? parecer.slice(0, 120) : "Rentabilidade por PDV e turno no período.",
      where: (cockpit.pdvsCriticos || [])[0]?.pdvCodigo ? `PDV ${cockpit.pdvsCriticos[0].pdvCodigo}` : "Rede consolidada",
      actionNow: (cockpit.pdvsCriticos || []).length
        ? "Intervir nos PDVs críticos de margem."
        : "Expandir boas práticas dos top PDVs.",
    }),
    detailBuilder: (cockpitDetail) => `
      ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      <p class="muted">F04.3 — Store & Shift Profitability</p>
      <div class="kpi-grid">
        <article class="kpi-card"><span class="kpi-label">Lucro Top 5 PDVs</span><strong>${fmtMoney(exec["17_lucroTop5Pdvs"])}</strong></article>
        <article class="kpi-card"><span class="kpi-label">Risco PDVs Críticos</span><strong>${fmtMoney(exec["18_riscoPdvsCriticos"])}</strong></article>
        <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
        <article class="kpi-card"><span class="kpi-label">Decisões Automáticas</span><strong>${exec["19_decisoesOperacionaisAutomaticas"] ? "Sim" : "Não"}</strong></article>
      </div>
      ${renderTable("Top PDVs", cockpitDetail.topPdvs, pdvCols)}
      ${renderTable("Top Turnos", cockpitDetail.topTurnos, turnCols)}
      ${renderTable("Top Operadores", cockpitDetail.topOperadores, [
        { key: "employeeName", label: "Operador" },
        { key: "receitaBruta", label: "Receita", money: true },
        { key: "resultadoLiquido", label: "Resultado", money: true },
        { key: "profitabilityScore", label: "Score" },
        { key: "profitabilityBand", label: "Banda", band: true },
      ])}
      ${renderTable("PDVs Críticos", cockpitDetail.pdvsCriticos, pdvCols)}
      ${renderTable("Turnos Críticos", cockpitDetail.turnosCriticos, turnCols)}
      ${renderTable("ROI Operacional (PDV + Turno)", cockpitDetail.roiOperacional, [
        { key: "pdvCodigo", label: "PDV" },
        { key: "turno", label: "Turno" },
        { key: "resultadoLiquido", label: "Resultado", money: true },
        { key: "roi", label: "ROI" },
      ])}`,
    refreshButtonId: "opRoiRefresh",
    exportButtonId: "opRoiExport",
    exportData: cockpit.topPdvs || [],
    exportFileName: `operation_roi_${filters?.dataInicial}_${filters?.dataFinal}.csv`,
    defaultView: "operationRoi",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
