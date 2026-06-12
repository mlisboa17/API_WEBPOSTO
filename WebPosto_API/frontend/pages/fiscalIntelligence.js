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

export function renderFiscalIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Fiscal Intelligence…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const tax = payload.taxClassificationEngine || cockpit.taxClassification || {};
  const risks = payload.fiscalRiskEngine?.risks || cockpit.topRiscos || [];
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Fiscal Intelligence</h2>
        <p class="muted">F06.3 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="fiscalIntelRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="fiscalIntelExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Produtos</span><strong>${exec["1_totalProdutos"] ?? cockpit.produtos ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Com NCM (evid.)</span><strong>${exec["2_comNcm"] ?? cockpit.ncmComEvidencia ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Sem NCM (evid.)</span><strong>${exec["3_semNcm"] ?? cockpit.ncmSemEvidencia ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Cobertura Fiscal</span><strong>${exec["4_coberturaFiscalAtual"] ?? cockpit.coberturaFiscal ?? "—"}%</strong></article>
      <article class="kpi-card"><span class="kpi-label">Tributação</span><strong>${exec["5_coberturaTributaria"] ?? cockpit.classificacaoTributaria ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Riscos</span><strong>${exec["6_riscosFiscais"] ?? cockpit.riscosFiscais ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Maior Risco</span><strong>${exec["7_maiorRisco"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">DRE Possível</span><strong>${exec["10_drePossivel"] ? "Sim" : "Não"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Aprovado F06.4</span><strong>${exec["20_aprovadoF064"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Classificação Tributária", tax.items || [], [
      { key: "tributo", label: "Tributo" },
      { key: "classificacao", label: "Status" },
      { key: "evidencia", label: "Evidência" },
    ])}
    ${renderTable("Top Riscos Fiscais", risks.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "segmento", label: "Segmento" },
      { key: "risco", label: "Risco" },
      { key: "tipo", label: "Tipo" },
    ])}
  `;

  node.querySelector("#fiscalIntelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#fiscalIntelExport")?.addEventListener("click", () => {
    downloadCsv("fiscal-intelligence-risks.csv", risks);
  });
}
