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
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Learning Engine…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const feedback = payload.executiveFeedbackLoop?.items || cockpit.executiveFeedback || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Closed Loop Learning Engine</h2>
        <p class="muted">F05.5 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="learningRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="learningExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Avaliadas</span><strong>${exec["1_recomendacoesAvaliadas"] ?? cockpit.totalAvaliadas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Efetivas</span><strong>${exec["2_efetivas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Inefetivas</span><strong>${exec["3_inefetivas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Taxa de Acerto</span><strong>${exec["4_taxaAcerto"] ?? cockpit.taxaAcerto ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Previsto Médio</span><strong>${fmtMoney(exec["5_roiPrevistoMedio"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Realizado Médio</span><strong>${fmtMoney(exec["6_roiRealizadoMedio"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Score Histórico</span><strong>${exec["12_scoreHistoricoMedio"] ?? cockpit.precisaoHistorica ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprendizado Acumulado</span><strong>${exec["13_aprendizadoAcumulado"] ?? cockpit.aprendizadoAcumulado ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F06</span><strong>${exec["20_aprovadoF06"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderFeedback(feedback)}
    ${renderTable("ROI Previsto vs Realizado", cockpit.roiPrevistoVsRealizado, [
      { key: "recommendationId", label: "ID" },
      { key: "roiPrevisto", label: "Previsto", money: true },
      { key: "roiRealizado", label: "Realizado", money: true },
      { key: "deltaROI", label: "Δ ROI", money: true },
      { key: "acuraciaROI", label: "Acurácia %" },
    ])}
    ${renderTable("Top Recomendações", cockpit.topRecomendacoes, [
      { key: "titulo", label: "Título" },
      { key: "historicalScore", label: "Score" },
      { key: "learningScore", label: "Learning" },
      { key: "confidenceAdjustment", label: "Δ Conf." },
    ])}
    ${renderTable("Piores Recomendações", cockpit.pioresRecomendacoes, [
      { key: "titulo", label: "Título" },
      { key: "historicalScore", label: "Score" },
      { key: "learningScore", label: "Learning" },
    ])}
  `;

  node.querySelector("#learningRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#learningExport")?.addEventListener("click", () => {
    downloadCsv("learning.csv", cockpit.topRecomendacoes || []);
  });
}
