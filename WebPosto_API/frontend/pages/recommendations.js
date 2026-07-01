import { formatCurrency } from "../services/format.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

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
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Autonomous Recommendation Engine",
    actionsHtml: `
      <button type="button" id="recommendationsRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="recommendationsExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const feed = cockpitDetail.executiveFeed || payloadDetail.executiveFeedEngine?.items || [];
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${renderFeed(feed)}
        ${renderTable("Top Recomendações", cockpitDetail.topRecomendacoes, REC_COLUMNS)}
        ${renderTable("Top Oportunidades", cockpitDetail.topOportunidades, REC_COLUMNS)}
        ${renderTable("Top Riscos", cockpitDetail.topRiscos, REC_COLUMNS)}
        ${renderTable("Prioridade P1", cockpitDetail.prioridade1, REC_COLUMNS)}
      `;
    },
    refreshButtonId: "recommendationsRefresh",
    exportButtonId: "recommendationsExport",
    exportData: cockpit.topRecomendacoes || [],
    exportFileName: "recommendations.csv",
    defaultView: "recommendations",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
