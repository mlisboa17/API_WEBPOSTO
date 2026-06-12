import { downloadCsv } from "../services/export.js";

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .filter(Boolean)
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          return `<td>${val ?? "—"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderCommercialExecution(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Execução Comercial…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const assignment = payload.commercialAssignmentEngine || {};
  const tracking = payload.commercialExecutionTracking || {};
  const evidence = payload.commercialEvidenceEngine || {};
  const outcome = payload.commercialOutcomeMeasurement || payload.outcomeAntesDepois || {};
  const revenue = payload.revenueLiftTracking || {};
  const margin = payload.marginImprovementTracking || {};
  const performance = payload.commercialPerformance || {};
  const acoes = assignment.actions || cockpit.planoAcao || [];
  const events = tracking.events || [];
  const evidences = evidence.evidences || [];
  const owners = performance.porResponsavel || [];
  const filiais = performance.porFilial || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Execução Comercial Produtos Vendidos</h2>
        <p class="muted">F07.7 · Execução · Evidência · Outcome · ROI Real · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="commercialExecRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="commercialExecExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Total ações</span><strong>${exec["1_totalAcoes"] ?? cockpit.totalAcoes ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Executadas</span><strong>${exec["2_acoesExecutadas"] ?? cockpit.acoesExecutadas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Validadas</span><strong>${exec["3_acoesValidadas"] ?? cockpit.acoesValidadas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Canceladas</span><strong>${exec["4_acoesCanceladas"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Receita realizada</span><strong>R$ ${exec["6_receitaRealizada"] ?? revenue.receitaRealizada ?? cockpit.receitaRealizada ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Delta receita</span><strong>R$ ${exec["7_deltaReceita"] ?? revenue.deltaReceita ?? cockpit.deltaReceita ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Margem realizada</span><strong>R$ ${exec["9_margemRealizada"] ?? margin.margemRealizada ?? cockpit.margemRealizada ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Taxa execução</span><strong>${exec["15_taxaExecucaoPct"] ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Taxa validação</span><strong>${exec["16_taxaValidacaoPct"] ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F07.8</span><strong>${exec["20_aprovadoF078"] ? "Sim" : "Não"}</strong></article>
    </div>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Receita antes</span><strong>R$ ${outcome.antes?.receitaProdutosVendidos ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Receita depois</span><strong>R$ ${outcome.depois?.receitaProdutosVendidos ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Margem antes</span><strong>R$ ${outcome.antes?.margemBruta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Margem depois</span><strong>R$ ${outcome.depois?.margemBruta ?? "—"}</strong></article>
    </div>
    ${renderTable("Plano de execução", acoes.slice(0, 12), [
      { key: "actionId", label: "Ação" },
      { key: "tipo", label: "Tipo" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "responsavelNome", label: "Responsável" },
      { key: "prioridade", label: "Prioridade" },
      { key: "lifecycleStatus", label: "Status" },
      { key: "receitaRealizada", label: "Receita real", render: (r) => `R$ ${r.receitaRealizada ?? "—"}` },
      { key: "roiReal", label: "ROI real", render: (r) => (r.roiRealCalculavel ? `R$ ${r.roiReal}` : "—") },
    ])}
    ${renderTable("Eventos de execução", events.slice(0, 10), [
      { key: "actionId", label: "Ação" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "responsavel", label: "Executor" },
      { key: "dataExecucao", label: "Data" },
      { key: "lifecycleStatus", label: "Status" },
    ])}
    ${renderTable("Evidências", evidences.slice(0, 10), [
      { key: "actionId", label: "Ação" },
      { key: "executionDate", label: "Data" },
      { key: "executionUser", label: "Usuário" },
      { key: "executionComment", label: "Comentário" },
    ])}
    ${renderTable("Performance por responsável", owners.slice(0, 8), [
      { key: "responsavel", label: "Responsável" },
      { key: "executadas", label: "Executadas" },
      { key: "validadas", label: "Validadas" },
      { key: "receitaRealizada", label: "Receita", render: (r) => `R$ ${r.receitaRealizada ?? "—"}` },
    ])}
    ${renderTable("Performance por filial", filiais.slice(0, 8), [
      { key: "empresaCodigo", label: "Filial" },
      { key: "executadas", label: "Executadas" },
      { key: "validadas", label: "Validadas" },
      { key: "receitaRealizada", label: "Receita", render: (r) => `R$ ${r.receitaRealizada ?? "—"}` },
    ])}
  `;

  node.querySelector("#commercialExecRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#commercialExecExport")?.addEventListener("click", () => {
    downloadCsv("commercial_execution.csv", acoes, [
      "actionId",
      "tipo",
      "empresaCodigo",
      "responsavelNome",
      "prioridade",
      "lifecycleStatus",
      "receitaPrevista",
      "receitaRealizada",
      "margemRealizada",
      "roiReal",
    ]);
  });
}
