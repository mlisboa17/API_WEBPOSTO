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

export function renderLmcIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando LMC Intelligence…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const recon = payload.fuelReconciliationEngine || cockpit.reconciliacao || {};
  const loss = payload.lossSurplusEngine || {};
  const tanks = payload.tankIntelligence?.tanquesCriticos || cockpit.topTanques || [];
  const pumps = payload.pumpIntelligence || {};
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>LMC Intelligence</h2>
        <p class="muted">F06.2 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="lmcIntelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="lmcIntelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Perdas</span><strong>${exec["4_perdaTotal"] ?? cockpit.perdas ?? "—"} L</strong></article>
      <article class="kpi-card"><span class="kpi-label">Sobras</span><strong>${exec["5_sobraTotal"] ?? cockpit.sobras ?? "—"} L</strong></article>
      <article class="kpi-card"><span class="kpi-label">Índice Perda</span><strong>${exec["6_indicePerda"] ?? cockpit.indicePerda ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Risco Combustível</span><strong>${exec["13_maiorRisco"] ?? cockpit.riscoCombustivel ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Vendido (LMC)</span><strong>${exec["2_totalVendido"] ?? "—"} L</strong></article>
      <article class="kpi-card"><span class="kpi-label">Conciliação</span><strong>${exec["3_totalConciliado"] ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Filial Crítica</span><strong>${exec["7_filialMaisCritica"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Endpoint Bico</span><strong>${exec["endpointBicoDedicado"] ?? pumps.classificacaoEndpointDedicado ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F06.3</span><strong>${exec["20_aprovadoF063"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top Tanques", tanks, [
      { key: "tanqueCodigo", label: "Tanque" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "perda", label: "Perda (L)" },
      { key: "sobra", label: "Sobra (L)" },
    ])}
    ${renderTable("Top Divergências", cockpit.topDivergencias || recon.items || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Quantidade" },
    ])}
    ${renderTable("Bicos Críticos (nested LMC)", pumps.bicosCriticos || [], [
      { key: "bicoCodigo", label: "Bico" },
      { key: "status", label: "Status" },
      { key: "vendaLitros", label: "Venda (L)" },
      { key: "fonte", label: "Fonte" },
    ])}
  `;

  node.querySelector("#lmcIntelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#lmcIntelExport")?.addEventListener("click", () => {
    downloadCsv("lmc-intelligence-tanks.csv", tanks);
  });
}
