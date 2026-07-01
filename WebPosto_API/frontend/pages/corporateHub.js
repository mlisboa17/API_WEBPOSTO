import { formatCurrency } from "../services/format.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function label(item, nameKey = "employeeName", codeKey = "funcionarioCodigo") {
  if (!item) return "—";
  if (typeof item === "string") return item;
  const name = item[nameKey] || item.nomeFilial || item.title || item.nome;
  const code = item[codeKey] ?? item.empresaCodigo ?? item.pdvCodigo ?? item.type;
  return name ? `${name} (${code})` : String(code ?? "—");
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .filter(Boolean)
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

export function renderCorporateHub(node, payload, filters, options = {}) {
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Corporate Intelligence Hub",
    actionsHtml: `
      <button type="button" id="corporateHubRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="corporateHubExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const parecer = payloadDetail.parecerFinal || "";
      const decisao = payloadDetail.decisaoArquitetural || {};
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${decisao.justificativa ? `<p class="muted">${decisao.justificativa}</p>` : ""}
        ${renderTable("Top Oportunidades", cockpitDetail.topOportunidades, [
          { key: "prioridade", label: "Prioridade" },
          { key: "title", label: "Oportunidade" },
          { key: "impactoEstimado", label: "Impacto", money: true },
        ])}
        ${renderTable("Top Riscos", cockpitDetail.topRiscos, [
          { key: "severity", label: "Severidade" },
          { key: "riskType", label: "Tipo" },
          { key: "message", label: "Mensagem" },
        ])}
        ${renderTable("Top Operadores", cockpitDetail.topOperadores, [
          { key: "employeeName", label: "Operador", render: (r) => label(r) },
          { key: "benchmarkScore", label: "Score" },
        ])}
        ${renderTable("Alertas Corporativos", cockpitDetail.alertasCorporativos, [
          { key: "severity", label: "Severidade" },
          { key: "category", label: "Categoria" },
          { key: "message", label: "Mensagem" },
        ])}
      `;
    },
    refreshButtonId: "corporateHubRefresh",
    exportButtonId: "corporateHubExport",
    exportData: cockpit.topOportunidades || [],
    exportFileName: "corporate-hub.csv",
    defaultView: "corporateHub",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
