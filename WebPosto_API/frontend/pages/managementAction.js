import { formatCurrency } from "../services/format.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function opLabel(item) {
  if (!item) return "—";
  const name = item.employeeName || item.employeeName;
  const code = item.funcionarioCodigo;
  return name ? `${name} (${code})` : String(code ?? "—");
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
  return `
    <section class="panel">
      <h3>${title}</h3>
      <table class="data-table">
        <thead><tr>${head}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </section>`;
}

const actionCols = [
  { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
  { key: "primaryAction", label: "Ação Principal" },
  { key: "globalScore", label: "Score" },
  { key: "riskScore", label: "Risco" },
];

const promoCols = [
  { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
  { key: "motivo", label: "Motivo" },
  { key: "globalScore", label: "Score" },
  { key: "roiNorm", label: "ROI" },
];

const bonusCols = [
  { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
  { key: "bonusRecomendado", label: "Bônus", money: true },
  { key: "bonusRoiEsperado", label: "ROI Esperado" },
];

const trainCols = [
  { key: "employeeName", label: "Operador", render: (r) => opLabel(r) },
  {
    key: "categories",
    label: "Categorias",
    render: (r) => (r.categories || []).join(", ") || "—",
  },
];

const pdvCols = [
  { key: "pdvCodigo", label: "PDV" },
  { key: "receitaBruta", label: "Receita", money: true },
  { key: "destruicaoMargem", label: "Destruição", money: true },
  { key: "roi", label: "ROI" },
];

const turnCols = [
  { key: "turno", label: "Turno" },
  { key: "receitaBruta", label: "Receita", money: true },
  { key: "shiftRiskScore", label: "Risco" },
];

export function renderManagementAction(node, payload, filters, options = {}) {
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Management Action Center",
    actionsHtml: `
      <button type="button" id="macRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="macExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${renderTable("Ações Pendentes", cockpitDetail.acoesPendentes, actionCols)}
        ${renderTable("Promoções", cockpitDetail.promocoes, promoCols)}
        ${renderTable("Bonificações", cockpitDetail.bonificacoes, bonusCols)}
        ${renderTable("Treinamentos", cockpitDetail.treinamentos, trainCols)}
        ${renderTable("Auditorias", cockpitDetail.auditorias, actionCols)}
        ${renderTable("PDVs Críticos", cockpitDetail.pdvsCriticos, pdvCols)}
        ${renderTable("Turnos Críticos", cockpitDetail.turnosCriticos, turnCols)}
      `;
    },
    refreshButtonId: "macRefresh",
    exportButtonId: "macExport",
    exportData: cockpit.acoesPendentes || [],
    exportFileName: `management_action_${filters?.dataInicial}_${filters?.dataFinal}.csv`,
    defaultView: "managementAction",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
