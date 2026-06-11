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

function renderFeed(items) {
  if (!items?.length) return "";
  const cards = items
    .map(
      (item) => `
    <article class="panel copilot-answer">
      <p><strong>${item.headline || "—"}</strong></p>
      <p class="muted">Prioridade: ${item.prioridade || "—"} · Impacto: ${fmtMoney(item.impacto)} · ROI previsto: ${fmtMoney(item.roi)}</p>
    </article>
  `
    )
    .join("");
  return `<section class="panel"><h3>Feed Executivo</h3>${cards}</section>`;
}

const REC_COLUMNS = [
  { key: "priority", label: "P" },
  { key: "tipo", label: "Tipo" },
  { key: "titulo", label: "Título" },
  { key: "classificacao", label: "Classificação" },
  { key: "roiMedio", label: "ROI Médio", money: true },
  { key: "confidenceLevel", label: "Confiança" },
  { key: "lifecycleStatus", label: "Lifecycle" },
];

export function renderRecommendations(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Recommendation Engine…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const feed = cockpit.executiveFeed || payload.executiveFeedEngine?.items || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Autonomous Recommendation Engine</h2>
        <p class="muted">F05.4 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="recommendationsRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="recommendationsExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Recomendações</span><strong>${exec["1_totalRecomendacoes"] ?? cockpit.totalRecomendacoes ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Oportunidades</span><strong>${exec["2_oportunidadesDetectadas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Riscos</span><strong>${exec["3_riscosDetectados"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">P1</span><strong>${exec["4_prioridadeP1"] ?? (cockpit.prioridade1 || []).length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">P2</span><strong>${exec["5_prioridadeP2"] ?? (cockpit.prioridade2 || []).length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">P3</span><strong>${exec["6_prioridadeP3"] ?? (cockpit.prioridade3 || []).length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Previsto Total</span><strong>${fmtMoney(cockpit.roiPrevistoTotal)}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Auditável</span><strong>${exec["19_motorAuditavel"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F05.5</span><strong>${exec["20_aprovadoF055"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderFeed(feed)}
    ${renderTable("Top Recomendações", cockpit.topRecomendacoes, REC_COLUMNS)}
    ${renderTable("Top Oportunidades", cockpit.topOportunidades, REC_COLUMNS)}
    ${renderTable("Top Riscos", cockpit.topRiscos, REC_COLUMNS)}
    ${renderTable("Prioridade P1", cockpit.prioridade1, REC_COLUMNS)}
  `;

  node.querySelector("#recommendationsRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#recommendationsExport")?.addEventListener("click", () => {
    downloadCsv("recommendations.csv", cockpit.topRecomendacoes || []);
  });
}
