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

export function renderLmcIntelligence(node, payload, filters, options = {}) {
  const tanks = payload?.tankIntelligence?.tanquesCriticos || payload?.cockpit?.topTanques || [];

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Controle LMC",
    actionsHtml: `
      <button type="button" id="lmcIntelRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="lmcIntelExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpit, payloadDetail) => {
      const recon = payloadDetail.fuelReconciliationEngine || cockpit.reconciliacao || {};
      const pumps = payloadDetail.pumpIntelligence || {};
      const tanksDetail = payloadDetail.tankIntelligence?.tanquesCriticos || cockpit.topTanques || [];
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${renderTable("Top Tanques", tanksDetail, [
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
    },
    refreshButtonId: "lmcIntelRefresh",
    exportButtonId: "lmcIntelExport",
    exportData: tanks,
    exportFileName: "lmc-intelligence-tanks.csv",
    defaultView: "lmcIntelligence",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
