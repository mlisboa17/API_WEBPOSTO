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

function renderFeedback(items) {
  if (!items?.length) return "";
  const cards = items
    .map(
      (item) => `
    <article class="panel copilot-answer">
      <p><strong>${item.headline || "—"}</strong></p>
      <p class="muted">Taxa: ${item.taxaAcerto ?? "—"}% · Amostra: ${item.amostra ?? "—"}</p>
    </article>
  `
    )
    .join("");
  return `<section class="panel"><h3>Feedback Executivo</h3>${cards}</section>`;
}

export function renderLearning(node, payload, filters, options = {}) {
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Closed Loop Learning Engine",
    actionsHtml: `
      <button type="button" id="learningRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="learningExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const feedback = payloadDetail.executiveFeedbackLoop?.items || cockpitDetail.executiveFeedback || [];
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${renderFeedback(feedback)}
        ${renderTable("ROI Previsto vs Realizado", cockpitDetail.roiPrevistoVsRealizado, [
          { key: "recommendationId", label: "ID" },
          { key: "roiPrevisto", label: "Previsto", money: true },
          { key: "roiRealizado", label: "Realizado", money: true },
          { key: "deltaROI", label: "Δ ROI", money: true },
          { key: "acuraciaROI", label: "Acurácia %" },
        ])}
        ${renderTable("Top Recomendações", cockpitDetail.topRecomendacoes, [
          { key: "titulo", label: "Título" },
          { key: "historicalScore", label: "Score" },
          { key: "learningScore", label: "Learning" },
          { key: "confidenceAdjustment", label: "Δ Conf." },
        ])}
        ${renderTable("Piores Recomendações", cockpitDetail.pioresRecomendacoes, [
          { key: "titulo", label: "Título" },
          { key: "historicalScore", label: "Score" },
          { key: "learningScore", label: "Learning" },
        ])}
      `;
    },
    refreshButtonId: "learningRefresh",
    exportButtonId: "learningExport",
    exportData: cockpit.topRecomendacoes || [],
    exportFileName: "learning.csv",
    defaultView: "learning",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
