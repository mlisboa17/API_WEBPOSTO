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
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Produtos Vendidos</h2>
        <p class="muted">F07.3 · Otimização catálogo · empresaCodigo · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="nonFuelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="nonFuelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Receita Produtos Vendidos</span><strong>R$ ${exec["10_receitaProdutosVendidos"] ?? cockpit.receitaProdutosVendidos ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Recuperados</span><strong>${recovery.produtosRecuperados ?? cockpit.produtosRecuperados ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Pendentes</span><strong>${cockpit.produtosPendentes ?? exec["3_produtosSemCadastroRestantes"] ?? recovery.depoisSemMatch ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Cobertura catálogo</span><strong>${coverage.coberturaCatalogoFinalPct ?? cockpit.coberturaCatalogoFinalPct ?? exec["4_coberturaCatalogoFinal"] ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Lookup</span><strong>${cockpit.performanceLookupSec ?? benchmark.tempoTotalLookupDepoisSec ?? "—"}s</strong></article>
      <article class="kpi-card"><span class="kpi-label">Cache hit</span><strong>${cockpit.cacheHitRatePct ?? cache.cacheHitRatePct ?? exec["9_cacheHitRate"] ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">SKU residual</span><strong>${forensics.classificacaoFinal ?? cockpit.residualClassificacao ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Redução lookup</span><strong>${benchmark.reducaoPercentual ?? exec["7_reducaoPercentual"] ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F07.4</span><strong>${exec["20_aprovadoF074"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top produtos", ranking.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "qtd", label: "Qtd" },
      { key: "valor", label: "Valor R$", render: (r) => (r.valor != null ? Number(r.valor).toFixed(2) : "—") },
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
    downloadCsv("produtos-vendidos-ranking.csv", ranking);
  });
}
