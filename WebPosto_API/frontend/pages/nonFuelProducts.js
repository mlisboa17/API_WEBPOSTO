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
  const filialDestaque = cockpit.filialDestaque || (margin.porFilial || [])[0] || {};
  const oportunidades = opportunities.oportunidades || cockpit.oportunidades || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Produtos Vendidos</h2>
        <p class="muted">F07.5 · Decisão comercial · sortimento e oportunidade · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="nonFuelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="nonFuelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Top margem</span><strong>${exec["1_produtoMaiorMargemPct"] ?? topMargem[0]?.produtoCodigo ?? "—"} (${exec["2_margemPctLider"] ?? topMargem[0]?.margemPct ?? "—"}%)</strong></article>
      <article class="kpi-card"><span class="kpi-label">Alertas baixa margem</span><strong>${exec["3_produtosAltoVolumeBaixaMargem"] ?? lowMargin.totalAlertas ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Potencial expansão</span><strong>${exec["5_produtosPotencialExpansao"] ?? expansion.totalPotencial ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Filiais abaixo benchmark</span><strong>${exec["7_filiaisAbaixoBenchmarkMix"] ?? benchmarkGap.totalAbaixoBenchmark ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Foco comercial</span><strong>${exec["9_produtosFocoComercial"] ?? commercialFocus.totalFoco ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Dep. combustível</span><strong>${exec["11_filiaisDependenciaCombustivel"] ?? fuelRisk.totalFiliaisRisco ?? "—"} filiais</strong></article>
      <article class="kpi-card"><span class="kpi-label">Receita PV</span><strong>R$ ${exec["4_receitaProdutosVendidos"] ?? margin.receitaProdutosVendidos ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Margem bruta</span><strong>${exec["6_margemBrutaPct"] ?? margin.margemBrutaPct ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F07.6</span><strong>${exec["20_aprovadoF076"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Maior margem — priorizar proteção", topMargem.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "margemPct", label: "Margem %", render: (r) => `${r.margemPct ?? "—"}%` },
      { key: "margemBruta", label: "Margem R$", render: (r) => (r.margemBruta != null ? Number(r.margemBruta).toFixed(2) : "—") },
      { key: "receita", label: "Receita R$", render: (r) => (r.receita != null ? Number(r.receita).toFixed(2) : "—") },
    ])}
    ${renderTable("Alto volume · baixa margem — revisar", alertasMargem.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "quantidade", label: "Qtd" },
      { key: "margemPct", label: "Margem %", render: (r) => `${r.margemPct ?? "—"}%` },
      { key: "gapMargemPct", label: "Gap %", render: (r) => `${r.gapMargemPct ?? "—"}%` },
    ])}
    ${renderTable("Potencial de expansão", potencialExpansao.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "qtdFiliais", label: "Filiais ativas" },
      { key: "coberturaFiliaisPct", label: "Cobertura %", render: (r) => `${r.coberturaFiliaisPct ?? "—"}%` },
      { key: "recomendacao", label: "Ação" },
    ])}
    ${renderTable("Filiais abaixo do benchmark de mix", filiaisAbaixo.slice(0, 8), [
      { key: "empresaCodigo", label: "Filial" },
      { key: "empresaNome", label: "Nome", render: (r) => r.empresaNome ?? r.filial ?? "—" },
      { key: "mixProdutosVendidosPct", label: "Mix PV %" },
      { key: "benchmarkMixPvPct", label: "Benchmark %" },
      { key: "gapBenchmarkPct", label: "Gap %" },
    ])}
    ${renderTable("Foco comercial recomendado", produtosFoco.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "focoComercialScore", label: "Score" },
      { key: "acoesRecomendadas", label: "Ações", render: (r) => (r.acoesRecomendadas || []).join(", ") || "—" },
    ])}
    ${renderTable("Dependência excessiva de combustível", dependenciaComb.slice(0, 8), [
      { key: "empresaCodigo", label: "Filial" },
      { key: "empresaNome", label: "Nome", render: (r) => r.empresaNome ?? r.filial ?? "—" },
      { key: "dependenciaCombustivelPct", label: "Dep. comb. %" },
      { key: "mixProdutosVendidosPct", label: "Mix PV %" },
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
    downloadCsv("produtos-vendidos-foco-comercial.csv", produtosFoco.length ? produtosFoco : topRev.length ? topRev : ranking);
  });
}
