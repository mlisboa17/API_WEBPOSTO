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

export function renderNonFuelProducts(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Produtos Vendidos…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const ranking = payload.productRankingEngine?.rankingProdutos || cockpit.topProdutos || [];
  const depts =
    payload.departmentRefinement?.porDepartamento
      ? Object.entries(payload.departmentRefinement.porDepartamento).map(([departamento, qtd]) => ({
          departamento,
          itens: qtd,
        }))
      : payload.departmentIntelligence?.receitaPorDepartamento ||
        payload.productRankingEngine?.topDepartamentos ||
        cockpit.topDepartamentos ||
        [];
  const branch =
    payload.branchProductMix?.filiais ||
    payload.multiBranchProductScale?.catalogoPorFilial ||
    payload.branchProductAnalytics?.filiais ||
    cockpit.mixPorFilial ||
    [];
  const recovery = payload.productMatchRecovery || {};
  const coverage = payload.productMasterCoverage || payload.productCatalogCompleteness || {};
  const pareto = payload.productRevenueIntelligence?.pareto || cockpit.pareto8020 || [];
  const benchmark = payload.productPerformanceBenchmark || {};
  const forensics = payload.residualSkuForensics || {};
  const cache = payload.productCacheStrategy || {};
  const performance = payload.productSalesPerformance || {};
  const margin = payload.marginIntelligence || {};
  const mixHealth = payload.mixHealthCommercial || {};
  const opportunities = payload.opportunityEngine || {};
  const assortment = payload.productOpportunityAssortment || payload.assortmentIntelligence || {};
  const marginLeaders = assortment.marginLeaders || {};
  const lowMargin = assortment.highVolumeLowMargin || {};
  const expansion = assortment.expansionPotential || {};
  const benchmarkGap = assortment.branchBenchmarkGap || {};
  const commercialFocus = assortment.commercialFocus || {};
  const fuelRisk = assortment.fuelDependencyRisk || {};
  const topVol = performance.rankingVolume || cockpit.topProdutosVolume || [];
  const topRev = performance.rankingReceita || cockpit.topProdutosReceita || [];
  const topMargem = marginLeaders.rankingMargemPct || cockpit.topMargem || [];
  const alertasMargem = lowMargin.produtos || cockpit.alertasBaixaMargem || [];
  const potencialExpansao = expansion.produtos || cockpit.potencialExpansao || [];
  const filiaisAbaixo = benchmarkGap.filiaisAbaixoBenchmark || cockpit.filiaisAbaixoBenchmark || [];
  const produtosFoco = commercialFocus.produtosFoco || cockpit.produtosFocoComercial || [];
  const dependenciaComb = fuelRisk.filiaisRisco || cockpit.dependenciaCombustivel || [];
  const actionCenter = payload.commercialActionCenter || {};
  const acSummary = actionCenter.summary || {};
  const acoes = actionCenter.actions || cockpit.acoesComerciais || cockpit.acoesAltaPrioridade || [];
  const acoesAlta = cockpit.acoesAltaPrioridade || acoes.filter((a) => a.prioridade === "ALTA").slice(0, 8);
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Produtos Vendidos</h2>
        <p class="muted">F07.6 · Commercial Action Center · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="nonFuelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="nonFuelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Ações comerciais</span><strong>${exec["1_totalAcoesComerciais"] ?? acSummary.totalAcoes ?? cockpit.totalAcoes ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Alta prioridade</span><strong>${exec["2_acoesAltaPrioridade"] ?? acSummary.acoesAltaPrioridade ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Impacto receita</span><strong>R$ ${exec["3_impactoTotalReceita"] ?? acSummary.impactoTotalReceita ?? cockpit.impactoTotalReceita ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Impacto margem</span><strong>R$ ${exec["4_impactoTotalMargem"] ?? acSummary.impactoTotalMargem ?? cockpit.impactoTotalMargem ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Com responsável</span><strong>${exec["9_acoesComResponsavel"] ?? acSummary.acoesComResponsavel ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Com evidência</span><strong>${exec["8_acoesComEvidencia"] ?? acSummary.acoesComEvidencia ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">R04 margem</span><strong>${exec["18_r04MargemConfiavel"] ?? actionCenter.r04Gate?.confiabilidadeMargemPct ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F07.7</span><strong>${exec["20_aprovadoF077"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Plano de ação comercial", acoes.slice(0, 12), [
      { key: "id", label: "ID" },
      { key: "tipo", label: "Tipo" },
      { key: "titulo", label: "Ação" },
      { key: "prioridade", label: "Prioridade" },
      { key: "status", label: "Status" },
      { key: "responsavel", label: "Responsável", render: (r) => r.responsavel?.ownerName ?? "—" },
      { key: "impactoEstimadoReceita", label: "Impacto R$", render: (r) => (r.impactoEstimadoReceita != null ? Number(r.impactoEstimadoReceita).toFixed(2) : "—") },
      { key: "prazo", label: "Prazo" },
    ])}
    ${renderTable("Alta prioridade", acoesAlta.slice(0, 8), [
      { key: "tipo", label: "Tipo" },
      { key: "descricao", label: "Descrição" },
      { key: "produtoCodigo", label: "Produto" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "status", label: "Status" },
    ])}
    ${renderTable("Departamentos refinados", depts.slice(0, 8), [
      { key: "departamento", label: "Departamento", render: (r) => r.departamento ?? r.nome ?? "—" },
      { key: "itens", label: "Produtos", render: (r) => r.itens ?? r.qtd ?? "—" },
      { key: "receita", label: "Receita R$", render: (r) => (r.receita ?? r.valor) != null ? Number(r.receita ?? r.valor).toFixed(2) : "—" },
    ])}
    ${renderTable("Pareto 80/20", pareto.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "valor", label: "Receita R$", render: (r) => (r.valor != null ? Number(r.valor).toFixed(2) : "—") },
      { key: "cumPct", label: "Acum. %", render: (r) => `${r.cumPct ?? "—"}%` },
    ])}
    ${renderTable("Mix por filial", branch, [
      { key: "empresaCodigo", label: "Filial" },
      { key: "empresaNome", label: "Nome", render: (r) => r.empresaNome ?? r.nomeFilial ?? r.filial ?? "—" },
      { key: "mixProdutosVendidosPct", label: "Mix PV %", render: (r) => r.mixProdutosVendidosPct ?? "—" },
      { key: "dependenciaCombustivelPct", label: "Dep. comb. %" },
    ])}
  `;

  node.querySelector("#nonFuelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#nonFuelExport")?.addEventListener("click", () => {
    downloadCsv("produtos-vendidos-acoes-comerciais.csv", acoes.length ? acoes : produtosFoco);
  });
}
