import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

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
  const acoes =
    payload?.commercialAssignmentEngine?.actions || payload?.cockpit?.planoAcao || [];

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Execução Comercial Produtos Vendidos",
    actionsHtml: `
      <button type="button" id="commercialExecRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="commercialExecExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpit, payloadDetail, exec) => {
      const assignment = payloadDetail.commercialAssignmentEngine || {};
      const tracking = payloadDetail.commercialExecutionTracking || {};
      const evidence = payloadDetail.commercialEvidenceEngine || {};
      const outcome = payloadDetail.commercialOutcomeMeasurement || payloadDetail.outcomeAntesDepois || {};
      const acoesDetail = assignment.actions || cockpit.planoAcao || [];
      const events = tracking.events || [];
      const evidences = evidence.evidences || [];
      const performance = payloadDetail.commercialPerformance || {};
      const owners = performance.porResponsavel || [];
      const filiais = performance.porFilial || [];
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        <div class="kpi-grid">
          <article class="kpi-card"><span class="kpi-label">Receita antes</span><strong>R$ ${outcome.antes?.receitaProdutosVendidos ?? "—"}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Receita depois</span><strong>R$ ${outcome.depois?.receitaProdutosVendidos ?? "—"}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Margem antes</span><strong>R$ ${outcome.antes?.margemBruta ?? "—"}</strong></article>
          <article class="kpi-card"><span class="kpi-label">Margem depois</span><strong>R$ ${outcome.depois?.margemBruta ?? "—"}</strong></article>
        </div>
        ${renderTable("Plano de execução", acoesDetail.slice(0, 12), [
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
    },
    refreshButtonId: "commercialExecRefresh",
    exportButtonId: "commercialExecExport",
    exportData: acoes,
    exportFileName: "commercial_execution.csv",
    defaultView: "commercialExecution",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
