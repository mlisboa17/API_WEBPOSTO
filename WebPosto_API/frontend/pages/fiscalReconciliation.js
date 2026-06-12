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

export function renderFiscalReconciliation(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Fiscal Reconciliation Hub…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const risks = payload.fiscalRiskConsolidation?.risks || cockpit.riscoFiscalConsolidado || [];
  const parecer = payload.parecerFinal || "";
  const nfce = payload.nfceVendaReconciliation || cockpit.nfceReconciliation || {};
  const lmc = payload.lmcSalesReconciliation || cockpit.lmcReconciliation || {};
  const prod = payload.productSalesReconciliation || cockpit.productReconciliation || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Fiscal Reconciliation Hub</h2>
        <p class="muted">F06.4 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="fiscalReconRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="fiscalReconExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Vendas × NFCE</span><strong>${exec["1_vendasConciliadasNfce"] ?? nfce.nfceMatched ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Sem NFCE</span><strong>${exec["2_vendasSemNfce"] ?? nfce.vendaSemNfce ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Itens × Produto</span><strong>${exec["3_itensConciliadosProduto"] ?? prod.itensConciliados ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Produtos c/ NCM</span><strong>${exec["4_produtosComNcm"] ?? prod.produtosComNcm ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Litros × LMC</span><strong>${exec["5_litrosConciliadosLmc"] ?? lmc.litrosConciliados ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Litros sem LMC</span><strong>${exec["6_litrosSemLmc"] ?? lmc.litrosSemLmc ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Maior Risco</span><strong>${exec["9_maiorRiscoConsolidado"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">DRE Fiscal</span><strong>${exec["13_dreFiscalViavel"] ? "Viável" : "Parcial"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F06.5</span><strong>${exec["20_aprovadoF065"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Lineage Fiscal", cockpit.lineageFiscal || [], [
      { key: "vendaCodigo", label: "Venda" },
      { key: "vendaItemCodigo", label: "Item" },
      { key: "produtoCodigo", label: "Produto" },
      { key: "nfceCodigo", label: "NFCE" },
      { key: "lmcCodigo", label: "LMC" },
    ])}
    ${renderTable("Divergências NFCE", nfce.items || cockpit.divergenciasNfce || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Qtd" },
    ])}
    ${renderTable("Divergências LMC", cockpit.divergenciasLmc || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Qtd" },
    ])}
    ${renderTable("Risco Fiscal Consolidado", risks.slice(0, 8), [
      { key: "dominio", label: "Domínio" },
      { key: "risco", label: "Risco" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "produtoCodigo", label: "Produto" },
    ])}
  `;

  node.querySelector("#fiscalReconRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#fiscalReconExport")?.addEventListener("click", () => {
    downloadCsv("fiscal-reconciliation-risks.csv", risks);
  });
}
