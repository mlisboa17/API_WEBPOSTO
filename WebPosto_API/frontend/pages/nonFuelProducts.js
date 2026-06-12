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
  const topVol = performance.rankingVolume || cockpit.topProdutosVolume || [];
  const topRev = performance.rankingReceita || cockpit.topProdutosReceita || [];
  const filialDestaque = cockpit.filialDestaque || (margin.porFilial || [])[0] || {};
  const oportunidades = opportunities.oportunidades || cockpit.oportunidades || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Produtos Vendidos</h2>
        <p class="muted">F07.4 · Gestão comercial · empresaCodigo · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="nonFuelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="nonFuelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Receita Produtos Vendidos</span><strong>R$ ${exec["4_receitaProdutosVendidos"] ?? margin.receitaProdutosVendidos ?? cockpit.receitaProdutosVendidos ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Margem bruta</span><strong>R$ ${exec["5_margemBrutaTotal"] ?? margin.margemBrutaTotal ?? "—"} (${exec["6_margemBrutaPct"] ?? margin.margemBrutaPct ?? "—"}%)</strong></article>
      <article class="kpi-card"><span class="kpi-label">Top receita</span><strong>${exec["2_produtoMaiorReceita"] ?? performance.topProdutoReceita?.produtoCodigo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Top volume</span><strong>${exec["1_produtoMaisVendidoVolume"] ?? performance.topProdutoVolume?.produtoCodigo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Filial destaque</span><strong>${exec["3_filialMelhorPerformance"] ?? filialDestaque.empresaCodigo ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Mix saudável</span><strong>${exec["7_mixSaudavel"] ?? mixHealth.mixSaudavel ?? cockpit.mixSaudavel ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Participação PV</span><strong>${exec["12_participacaoProdutosVendidos"] ?? mixHealth.participacaoProdutosVendidosPct ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Oportunidades</span><strong>${exec["10_oportunidadesIdentificadas"] ?? opportunities.totalOportunidades ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Cobertura catálogo</span><strong>${exec["13_coberturaCatalogoPreservada"] ?? coverage.coberturaCatalogoFinalPct ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F07.5</span><strong>${exec["20_aprovadoF075"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top produtos por volume", topVol.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "qtd", label: "Qtd" },
      { key: "receita", label: "Receita R$", render: (r) => (r.receita != null ? Number(r.receita).toFixed(2) : "—") },
    ])}
    ${renderTable("Top produtos por receita", topRev.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "receita", label: "Receita R$", render: (r) => (r.receita != null ? Number(r.receita).toFixed(2) : "—") },
      { key: "margem", label: "Margem R$", render: (r) => (r.margem != null ? Number(r.margem).toFixed(2) : "—") },
    ])}
    ${renderTable("Margem por departamento", (margin.porDepartamento || []).slice(0, 8), [
      { key: "departamento", label: "Departamento" },
      { key: "receita", label: "Receita R$", render: (r) => (r.receita != null ? Number(r.receita).toFixed(2) : "—") },
      { key: "margemBruta", label: "Margem R$", render: (r) => (r.margemBruta != null ? Number(r.margemBruta).toFixed(2) : "—") },
      { key: "margemPct", label: "Margem %", render: (r) => `${r.margemPct ?? "—"}%` },
    ])}
    ${renderTable("Performance por filial", (margin.porFilial || []).slice(0, 8), [
      { key: "empresaCodigo", label: "Filial" },
      { key: "empresaNome", label: "Nome" },
      { key: "receita", label: "Receita R$", render: (r) => (r.receita != null ? Number(r.receita).toFixed(2) : "—") },
      { key: "margemBruta", label: "Margem R$", render: (r) => (r.margemBruta != null ? Number(r.margemBruta).toFixed(2) : "—") },
      { key: "margemPct", label: "Margem %", render: (r) => `${r.margemPct ?? "—"}%` },
    ])}
    ${renderTable("Oportunidades comerciais", oportunidades.slice(0, 6), [
      { key: "tipo", label: "Tipo" },
      { key: "prioridade", label: "Prioridade" },
      { key: "descricao", label: "Descrição" },
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
    downloadCsv("produtos-vendidos-receita.csv", topRev.length ? topRev : ranking);
  });
}
