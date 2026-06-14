import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function renderAnswerCard(item) {
  const labels = (item.labels || []).map((l) => `<span class="tag">${l}</span>`).join(" ");
  const lineage = (item.lineage || [])
    .slice(0, 2)
    .map((l) => `${l.origem}/${l.snapshot}`)
    .join(" · ");
  return `
    <article class="panel copilot-answer">
      <p><strong>${item.answer || "—"}</strong></p>
      <p class="muted">Confiança: ${item.confidenceLevel || "—"} ${labels}</p>
      ${lineage ? `<p class="muted">Lineage: ${lineage}</p>` : ""}
      ${item.blocked ? `<p class="warn">Resposta bloqueada — NÃO RESPONDÍVEL</p>` : ""}
    </article>
  `;
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

export function renderCommercialCopilot(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Commercial Copilot…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const faq = cockpit.perguntasHomologadas || payload.commercialReasoningEngine?.catalog || [];
  const recs = payload.commercialRecommendationEngine?.recommendations || cockpit.recomendacoes || [];
  const ac = payload.commercialActionCenterIntegration || {};
  const parecer = payload.parecerFinal || "";
  const kpis = cockpit.kpis || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Commercial Copilot</h2>
        <p class="muted">F07.9 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="commercialCopilotRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="commercialCopilotExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Perguntas Homologadas</span><strong>${exec["5_perguntasHomologadas"] ?? faq.length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Recomendações</span><strong>${exec["6_totalRecomendacoes"] ?? recs.length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Ações Validadas</span><strong>${exec["9_acoesValidadas"] ?? ac.acoesValidadas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Real</span><strong>${exec["10_roiRealCitavel"] ?? ac.acoesComRoiReal ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Trust</span><strong>${exec.trustExecutivo ?? kpis.trustExecutivo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Auditável</span><strong>${exec["16_auditavel"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F08.0</span><strong>${exec["20_aprovadoF080"] ? "Sim" : "Não"}</strong></article>
    </div>
    <section class="panel">
      <h3>Perguntar ao Copiloto Comercial</h3>
      <div class="copilot-ask-row">
        <input type="text" id="commercialCopilotQuestionInput" placeholder="Ex.: Qual produto gera mais receita?" class="copilot-input" />
        <button type="button" id="commercialCopilotAskBtn" class="btn-primary">Perguntar</button>
      </div>
      <div id="commercialCopilotAskResult"></div>
    </section>
    <section class="panel"><h3>Perguntas Homologadas (F07.9)</h3><div class="copilot-faq">${faq.slice(0, 6).map(renderAnswerCard).join("")}</div></section>
    ${renderTable("Recomendações Comerciais", recs.slice(0, 8), [
      { key: "classificacao", label: "Classificação" },
      { key: "tipo", label: "Tipo" },
      { key: "titulo", label: "Ação" },
      { key: "actionId", label: "actionId" },
      { key: "roiEstimado", label: "ROI Est.", money: true },
      { key: "confidenceLevel", label: "Confiança" },
    ])}
    ${renderTable("Action Center (READ ONLY)", ac.listagem || [], [
      { key: "actionId", label: "actionId" },
      { key: "tipo", label: "Tipo" },
      { key: "status", label: "Status" },
      { key: "roiReal", label: "ROI Real", money: true },
      { key: "empresaCodigo", label: "Filial" },
    ])}
  `;

  node.querySelector("#commercialCopilotRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#commercialCopilotExport")?.addEventListener("click", () => {
    downloadCsv("commercial-copilot.csv", recs);
  });
  node.querySelector("#commercialCopilotAskBtn")?.addEventListener("click", async () => {
    const input = node.querySelector("#commercialCopilotQuestionInput");
    const resultNode = node.querySelector("#commercialCopilotAskResult");
    const q = input?.value?.trim();
    if (!q || !options.onAsk) return;
    resultNode.innerHTML = `<p class="muted">Processando…</p>`;
    try {
      const data = await options.onAsk(q);
      const resp = data?.answer || data?.resposta || data;
      resultNode.innerHTML = renderAnswerCard(resp);
    } catch (err) {
      resultNode.innerHTML = `<p class="warn">Erro: ${err.message || err}</p>`;
    }
  });
}
