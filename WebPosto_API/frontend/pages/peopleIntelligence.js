import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function opLabel(item) {
  if (!item) return "—";
  const name = item.employeeName || item.funcionarioCodigo;
  const code = item.funcionarioCodigo;
  return code ? `${name} (${code})` : String(name || "—");
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
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando People Intelligence…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const classification = payload.classification || {};
  const parecer = payload.parecerFinal || "";

  const summaryCards = `
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">ELITE</span><strong>${exec["1_operadoresElite"] ?? classification.ELITE ?? 0}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Alta Performance</span><strong>${exec["2_operadoresAltaPerformance"] ?? classification["ALTA PERFORMANCE"] ?? 0}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Atenção</span><strong>${exec["3_operadoresAtencao"] ?? classification["ATENÇÃO"] ?? 0}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Críticos</span><strong>${exec["4_operadoresCriticos"] ?? classification["CRÍTICO"] ?? 0}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Elegíveis Bônus</span><strong>${(cockpit.elegiveisBonus || []).length}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
    </div>`;

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

  const trainingRows = (cockpit.necessitamTreinamento || []).map((r) => ({
    ...r,
    trainingCategories: Array.isArray(r.trainingCategories) ? r.trainingCategories.join(", ") : r.trainingCategories,
  }));

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>People Intelligence</h2>
        <p class="muted">F04.1 — Accountability & Incentive Engine · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="peopleRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="peopleExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    ${summaryCards}
    ${renderScoreTable("Top Operadores", cockpit.topOperadores, opCols)}
    ${renderScoreTable("Elegíveis para Bônus", cockpit.elegiveisBonus, opCols)}
    ${renderScoreTable("Necessitam Treinamento", trainingRows, trainingCols)}
    ${renderScoreTable("Operadores Críticos", cockpit.operadoresCriticos, opCols)}
    ${renderScoreTable("Ranking Geral", cockpit.rankingGeral, opCols)}
    <section class="panel">
      <h3>PDVs Críticos</h3>
      <p>${(cockpit.pdvsCriticos || exec["17_pdvsPrejudicamOperadores"] || []).join(", ") || "—"}</p>
      <p class="muted">Potencial recuperação: ${fmtMoney(exec["16_potencialRecuperacao"])} · Risco financeiro críticos: ${fmtMoney(exec["15_riscoFinanceiroCriticos"])}</p>
    </section>`;

  node.querySelector("#peopleRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#peopleExport")?.addEventListener("click", () => {
    const rows = cockpit.rankingGeral || [];
    downloadCsv(
      rows.map((r) => ({
        funcionarioCodigo: r.funcionarioCodigo,
        employeeName: r.employeeName,
        globalScore: r.globalScore,
        globalClassification: r.globalClassification,
        salesScore: r.salesScore,
        productivityScore: r.productivityScore,
        accountabilityScore: r.accountabilityScore,
        complianceScore: r.complianceScore,
        bonusEligibility: r.bonusEligibility,
      })),
      `people_intelligence_${filters?.dataInicial}_${filters?.dataFinal}`
    );
  });
}
