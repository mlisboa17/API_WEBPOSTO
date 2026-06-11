import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function renderAnswerCard(item) {
  const labels = (item.labels || []).map((l) => `<span class="tag">${l}</span>`).join(" ");
  return `
    <article class="panel copilot-answer">
      <p><strong>${item.answer || "—"}</strong></p>
      <p class="muted">Confiança: ${item.confidenceLevel || "—"} ${labels}</p>
      ${item.blocked ? `<p class="warn">Resposta bloqueada por governança G02</p>` : ""}
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

export function renderExecutiveCopilot(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Executive Copilot…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const faq = payload.conversationLayer?.frequentQuestions || [];
  const recs = payload.recommendationEngine?.recommendations || cockpit.acoesRecomendadas || [];
  const answers = cockpit.perguntasFrequentes || [];
  const parecer = payload.parecerFinal || "";
  const kpis = cockpit.kpis || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Executive Copilot</h2>
        <p class="muted">F05.3 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="copilotRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="copilotExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Perguntas Homologadas</span><strong>${exec["5_perguntasHomologadas"] ?? faq.length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Recomendações</span><strong>${exec["6_totalRecomendacoes"] ?? recs.length ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Com Evidência</span><strong>${exec["7_recomendacoesComEvidencia"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Trust Executivo</span><strong>${exec.trustExecutivo ?? kpis.trustExecutivo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">ROI Realizado</span><strong>${exec["9_roiRealizado"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Auditável</span><strong>${exec["16_auditavel"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F05.4</span><strong>${exec["20_aprovadoF054"] ? "Sim" : "Não"}</strong></article>
    </div>
    <section class="panel">
      <h3>Perguntar ao Copilot</h3>
      <div class="copilot-ask-row">
        <input type="text" id="copilotQuestionInput" placeholder="Ex.: Onde estamos perdendo dinheiro?" class="copilot-input" />
        <button type="button" id="copilotAskBtn" class="btn-primary">Perguntar</button>
      </div>
      <div id="copilotAskResult"></div>
    </section>
    <section class="panel"><h3>Perguntas Frequentes (catálogo G02)</h3><div class="copilot-faq">${answers.slice(0, 6).map(renderAnswerCard).join("")}</div></section>
    ${renderTable("Ações Recomendadas", recs.slice(0, 8), [
      { key: "classificacao", label: "Classificação" },
      { key: "acao", label: "Ação" },
      { key: "responsavel", label: "Responsável" },
      { key: "roiEstimado", label: "ROI Est.", money: true },
      { key: "confidenceLevel", label: "Confiança" },
      { key: "labels", label: "Labels", render: (r) => (r.labels || []).join(", ") },
    ])}
    ${renderTable("Prioridades (Action Center)", cockpit.prioridades || [], [
      { key: "acao", label: "Ação" },
      { key: "status", label: "Status" },
      { key: "ownerName", label: "Responsável" },
      { key: "roiLabel", label: "ROI" },
    ])}
    ${renderTable("Riscos", cockpit.riscos || [], [
      { key: "title", label: "Risco", render: (r) => r.title || r.nome || r.tipo },
      { key: "severidade", label: "Severidade", render: (r) => r.severidade || r.nivel },
    ])}
  `;

  node.querySelector("#copilotRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#copilotExport")?.addEventListener("click", () => {
    downloadCsv("executive-copilot.csv", recs);
  });
  node.querySelector("#copilotAskBtn")?.addEventListener("click", async () => {
    const input = node.querySelector("#copilotQuestionInput");
    const resultNode = node.querySelector("#copilotAskResult");
    const q = input?.value?.trim();
    if (!q || !options.onAsk) return;
    resultNode.innerHTML = `<p class="muted">Processando…</p>`;
    try {
      const data = await options.onAsk(q);
      const resp = data?.resposta || data;
      resultNode.innerHTML = renderAnswerCard(resp);
    } catch (err) {
      resultNode.innerHTML = `<p class="warn">Erro: ${err.message || err}</p>`;
    }
  });
}
