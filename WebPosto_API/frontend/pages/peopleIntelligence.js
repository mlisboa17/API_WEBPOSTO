import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";
import { buildFourQuestionBrief } from "../services/executiveBrief.js";
import { countKpi } from "../services/executiveKpis.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function bandClass(cls) {
  const map = {
    ELITE: "badge-success",
    "ALTA PERFORMANCE": "badge-info",
    NORMAL: "badge-muted",
    "ATENÇÃO": "badge-warn",
    CRÍTICO: "badge-danger",
    Elegível: "badge-success",
    Observação: "badge-warn",
    "Não Elegível": "badge-danger",
  };
  return map[cls] || "badge-muted";
}

function renderScoreTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = item[c.key];
          if (c.band) {
            return `<td><span class="badge ${bandClass(val)}">${val ?? "—"}</span></td>`;
          }
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

export function renderPeopleIntelligence(node, payload, filters, options = {}) {
  if (!node) return;

  const cockpit = payload?.cockpit || {};
  const exec = payload?.executiveAnswers || {};
  const classification = payload?.classification || {};
  const parecer = payload?.parecerFinal || "";
  const criticos = exec["4_operadoresCriticos"] ?? classification["CRÍTICO"] ?? 0;
  const elegiveis = (cockpit.elegiveisBonus || []).length;

  const opCols = [
    { key: "employeeName", label: "Operador" },
    { key: "globalScore", label: "Score Global" },
    { key: "globalClassification", label: "Classe", band: true },
    { key: "salesScore", label: "Vendas" },
    { key: "accountabilityScore", label: "Accountability" },
    { key: "complianceScore", label: "Compliance" },
    { key: "bonusEligibility", label: "Bônus", band: true },
  ];

  const trainingCols = [
    { key: "employeeName", label: "Operador" },
    { key: "trainingCategories", label: "Treinamento" },
    { key: "globalClassification", label: "Classe", band: true },
  ];

  const exportRows = (cockpit.rankingGeral || []).map((r) => ({
    funcionarioCodigo: r.funcionarioCodigo,
    employeeName: r.employeeName,
    globalScore: r.globalScore,
    globalClassification: r.globalClassification,
    salesScore: r.salesScore,
    productivityScore: r.productivityScore,
    accountabilityScore: r.accountabilityScore,
    complianceScore: r.complianceScore,
    bonusEligibility: r.bonusEligibility,
  }));

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "People Intelligence",
    actionsHtml: `
      <button type="button" id="peopleRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="peopleExport" class="btn-secondary">Exportar CSV</button>
    `,
    kpiOverrides: [
      { label: "Elite", value: countKpi(exec["1_operadoresElite"] ?? classification.ELITE ?? 0), trendPct: null, status: "ok" },
      {
        label: "Alta Perf.",
        value: countKpi(exec["2_operadoresAltaPerformance"] ?? classification["ALTA PERFORMANCE"] ?? 0),
        trendPct: null,
        status: "ok",
      },
      { label: "Críticos", value: countKpi(criticos), trendPct: null, status: Number(criticos) > 0 ? "crit" : "ok" },
      { label: "Elegíveis", value: countKpi(elegiveis), trendPct: null, status: "ok" },
    ],
    brief: buildFourQuestionBrief({
      what: `${exec["1_operadoresElite"] ?? classification.ELITE ?? 0} operadores ELITE · ${criticos} crítico(s).`,
      why: parecer ? parecer.slice(0, 120) : `${elegiveis} elegível(is) a bônus no período.`,
      where: (cockpit.pdvsCriticos || exec["17_pdvsPrejudicamOperadores"] || [])[0]
        ? `PDV ${(cockpit.pdvsCriticos || exec["17_pdvsPrejudicamOperadores"])[0]}`
        : "Rede consolidada",
      actionNow:
        Number(criticos) > 0
          ? "Plano de treinamento para operadores críticos."
          : elegiveis > 0
            ? "Validar elegibilidade de bônus."
            : "Manter accountability e compliance.",
    }),
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const execDetail = payloadDetail?.executiveAnswers || {};
      const trainingRows = (cockpitDetail.necessitamTreinamento || []).map((r) => ({
        ...r,
        trainingCategories: Array.isArray(r.trainingCategories) ? r.trainingCategories.join(", ") : r.trainingCategories,
      }));
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        <p class="muted">F04.1 — Accountability & Incentive Engine</p>
        <div class="kpi-grid">
          <article class="kpi-card"><span class="kpi-label">ELITE</span><strong>${execDetail["1_operadoresElite"] ?? classification.ELITE ?? 0}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Alta Performance</span><strong>${execDetail["2_operadoresAltaPerformance"] ?? classification["ALTA PERFORMANCE"] ?? 0}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Atenção</span><strong>${execDetail["3_operadoresAtencao"] ?? classification["ATENÇÃO"] ?? 0}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Críticos</span><strong>${execDetail["4_operadoresCriticos"] ?? classification["CRÍTICO"] ?? 0}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Elegíveis Bônus</span><strong>${(cockpitDetail.elegiveisBonus || []).length}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${execDetail.paridadeDelta ?? "—"}</strong></article>
        </div>
        ${renderScoreTable("Top Operadores", cockpitDetail.topOperadores, opCols)}
        ${renderScoreTable("Elegíveis para Bônus", cockpitDetail.elegiveisBonus, opCols)}
        ${renderScoreTable("Necessitam Treinamento", trainingRows, trainingCols)}
        ${renderScoreTable("Operadores Críticos", cockpitDetail.operadoresCriticos, opCols)}
        ${renderScoreTable("Ranking Geral", cockpitDetail.rankingGeral, opCols)}
        <section class="panel">
          <h3>PDVs Críticos</h3>
          <p>${(cockpitDetail.pdvsCriticos || execDetail["17_pdvsPrejudicamOperadores"] || []).join(", ") || "—"}</p>
          <p class="muted">Potencial recuperação: ${fmtMoney(execDetail["16_potencialRecuperacao"])} · Risco financeiro críticos: ${fmtMoney(execDetail["15_riscoFinanceiroCriticos"])}</p>
        </section>`;
    },
    refreshButtonId: "peopleRefresh",
    exportButtonId: "peopleExport",
    exportData: exportRows,
    exportFileName: `people_intelligence_${filters?.dataInicial}_${filters?.dataFinal}.csv`,
    defaultView: "peopleIntelligence",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
