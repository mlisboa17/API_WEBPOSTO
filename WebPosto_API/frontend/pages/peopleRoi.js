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

  const cockpit = payload?.cockpit || {};
  const exec = payload?.executiveAnswers || {};
  const parecer = payload?.parecerFinal || "";

  const cols = [
    { key: "employeeName", label: "Operador" },
    { key: "receitaBruta", label: "Receita", money: true },
    { key: "resultadoLiquido", label: "Resultado", money: true },
    { key: "roi", label: "ROI" },
    { key: "profitabilityScore", label: "Profit Score" },
    { key: "profitabilityBand", label: "Banda", band: true },
  ];

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "People ROI",
    actionsHtml: `
      <button type="button" id="roiRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="roiExport" class="btn-secondary">Exportar CSV</button>
    `,
    kpiOverrides: [
      { label: "Lucro Top 10", value: moneyKpi(exec["13_lucroTop10"]), trendPct: null, status: "ok" },
      { label: "Risco Críticos", value: moneyKpi(exec["14_riscoCriticos"]), trendPct: null, status: "crit" },
      { label: "Paridade Δ", value: String(exec.paridadeDelta ?? "—"), trendPct: null, status: "ok" },
      {
        label: "Meritocracia",
        value: exec["18_gestaoMeritocratica"] ? "Sim" : "Não",
        trendPct: null,
        status: exec["18_gestaoMeritocratica"] ? "ok" : "warn",
      },
    ],
    brief: buildFourQuestionBrief({
      what: `Lucro top 10: ${moneyKpi(exec["13_lucroTop10"])} · risco críticos ${moneyKpi(exec["14_riscoCriticos"])}.`,
      why: parecer ? parecer.slice(0, 120) : "Rentabilidade por operador consolidada no período.",
      where: (cockpit.topRisco || [])[0]?.employeeName || "Rede consolidada",
      actionNow: exec["18_gestaoMeritocratica"]
        ? "Revisar top ROI e auditoria de margem."
        : "Ativar gestão meritocrática e corrigir destruição de margem.",
    }),
    detailBuilder: (cockpitDetail) => `
      ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      <p class="muted">F04.2 — Profitability & Management Decision</p>
      <div class="kpi-grid">
        <article class="kpi-card"><span class="kpi-label">Lucro Top 10</span><strong>${fmtMoney(exec["13_lucroTop10"])}</strong></article>
        <article class="kpi-card"><span class="kpi-label">Risco Críticos</span><strong>${fmtMoney(exec["14_riscoCriticos"])}</strong></article>
        <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
        <article class="kpi-card"><span class="kpi-label">Meritocracia</span><strong>${exec["18_gestaoMeritocratica"] ? "Sim" : "Não"}</strong></article>
      </div>
      ${renderTable("Top ROI", cockpitDetail.topRoi, cols)}
      ${renderTable("Top Lucro", cockpitDetail.topLucro, cols)}
      ${renderTable("Top Risco Econômico", cockpitDetail.topRisco, [
        { key: "employeeName", label: "Operador" },
        { key: "destruicaoMargem", label: "Destruição", money: true },
        { key: "descontos", label: "Descontos", money: true },
        { key: "faltas", label: "Faltas", money: true },
      ])}
      ${renderTable("Top Bônus (ROI)", cockpitDetail.topBonus, [
        { key: "employeeName", label: "Operador" },
        { key: "bonusRoi", label: "Bonus ROI" },
        { key: "bonusCustoEstimado", label: "Custo Est.", money: true },
        { key: "resultadoLiquido", label: "Resultado", money: true },
      ])}
      ${renderTable("Top Auditoria", cockpitDetail.topAuditoria, [
        { key: "employeeName", label: "Operador" },
        { key: "primaryAction", label: "Ação" },
        { key: "profitabilityBand", label: "Banda", band: true },
        { key: "resultadoLiquido", label: "Resultado", money: true },
      ])}`,
    refreshButtonId: "roiRefresh",
    exportButtonId: "roiExport",
    exportData: cockpit.topRoi || [],
    exportFileName: `people_roi_${filters?.dataInicial}_${filters?.dataFinal}.csv`,
    defaultView: "peopleRoi",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
