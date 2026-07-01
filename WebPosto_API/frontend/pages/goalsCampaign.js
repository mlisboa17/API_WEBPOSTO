import { formatCurrency } from "../services/format.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function opLabel(item) {
  if (!item) return "—";
  return item.employeeName ? `${item.employeeName} (${item.funcionarioCodigo})` : String(item.funcionarioCodigo ?? "—");
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          if (c.money) return `<td>${fmtMoney(val)}</td>`;
          return `<td>${val ?? "—"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderGoalsCampaign(node, payload, filters, options = {}) {
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Goals & Campaigns",
    actionsHtml: `
      <button type="button" id="goalsRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="goalsExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const qa = payloadDetail.qa || {};
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${renderTable("Metas Ativas", cockpitDetail.metasAtivas, [
          { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
          { key: "goalType", label: "Tipo" },
          { key: "targetValue", label: "Meta", money: true },
        ])}
        ${renderTable("Campanhas", cockpitDetail.campanhas, [
          { key: "name", label: "Campanha" },
          { key: "status", label: "Status" },
          { key: "percentualMedio", label: "% Médio" },
          { key: "roiCampanha", label: "ROI", money: true },
        ])}
        ${renderTable("Ranking Operadores", cockpitDetail.ranking, [
          { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
          { key: "goalType", label: "Meta" },
          { key: "percentualAtingido", label: "% Atingido" },
          { key: "status", label: "Status" },
        ])}
        ${renderTable("Bônus Projetado", cockpitDetail.bonusProjetado, [
          { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
          { key: "elegivel", label: "Elegível", render: (r) => (r.elegivel ? "Sim" : "Não") },
          { key: "bonusSugerido", label: "Valor", money: true },
          { key: "roiEsperado", label: "ROI Esp.", money: true },
        ])}
        ${renderTable("Operadores Abaixo da Meta", cockpitDetail.operadoresAbaixoMeta, [
          { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
          { key: "goalType", label: "Meta" },
          { key: "percentualAtingido", label: "%" },
          { key: "gap", label: "Gap", money: true },
        ])}
        ${renderTable("Alertas", cockpitDetail.alertas, [
          { key: "tipo", label: "Tipo" },
          { key: "operador", label: "Operador" },
          { key: "pct", label: "%" },
        ])}
        <p class="muted">QA evidência: ${qa.evidenciaCompleta ? "100%" : "Pendente"} · RBAC: ${qa.rbacAplicado ? "OK" : "—"}</p>
      `;
    },
    refreshButtonId: "goalsRefresh",
    exportButtonId: "goalsExport",
    exportData: cockpit.ranking || [],
    exportFileName: `goals_campaign_${filters?.dataInicial}_${filters?.dataFinal}.csv`,
    defaultView: "goalsCampaign",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
