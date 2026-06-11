import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function labelAction(item) {
  if (!item) return "—";
  return item.acao || item.title || item.message || "—";
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

export function renderExecutiveDecision(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Executive Decision Engine…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const plano = payload.planoCorporativoConsolidado || {};
  const parecer = payload.parecerFinal || "";
  const decisao = payload.decisaoArquitetural || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Executive Decision Engine</h2>
        <p class="muted">F05.1 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${decisao.justificativa ? `<p class="muted">${decisao.justificativa}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="decisionEngineRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="decisionEngineExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Trust Executivo</span><strong>${cockpit.trustExecutivo ?? exec.trustExecutivo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Corporate Score</span><strong>${cockpit.corporateScore ?? exec.corporateScore ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Executive Score</span><strong>${cockpit.executiveScore ?? exec.executiveScore ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Impacto P1</span><strong>${fmtMoney(cockpit.impactoEsperado)}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Auditável</span><strong>${exec["18_motorAuditavel"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Pronto F05.2</span><strong>${exec["19_prontoF052"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top Decisões (Prioridade 1)", cockpit.topDecisoes || plano.prioridade1, [
      { key: "prioridade", label: "P" },
      { key: "dominio", label: "Domínio" },
      { key: "acao", label: "Ação", render: labelAction },
      { key: "roi", label: "ROI", money: true },
      { key: "prazo", label: "Prazo" },
    ])}
    ${renderTable("Top ROI", cockpit.topRoi ? [cockpit.topRoi] : [], [
      { key: "acao", label: "Ação", render: labelAction },
      { key: "roi", label: "ROI", money: true },
      { key: "impacto", label: "Impacto", money: true },
    ])}
    ${renderTable("Top Riscos", cockpit.topRiscos, [
      { key: "classificacaoRisco", label: "Estratégia" },
      { key: "acao", label: "Plano", render: labelAction },
      { key: "riscoNivel", label: "Severidade" },
    ])}
    ${renderTable("Plano de Ação", cockpit.planoAcao, [
      { key: "prioridade", label: "P" },
      { key: "dominio", label: "Domínio" },
      { key: "acao", label: "Ação", render: labelAction },
      { key: "impacto", label: "Impacto", money: true },
      { key: "prazo", label: "Prazo" },
      { key: "responsavel", label: "Responsável", render: (r) => r.responsavel?.nome || "—" },
    ])}
  `;

  node.querySelector("#decisionEngineRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#decisionEngineExport")?.addEventListener("click", () => {
    downloadCsv("decision-engine.csv", cockpit.planoAcao || []);
  });
}
