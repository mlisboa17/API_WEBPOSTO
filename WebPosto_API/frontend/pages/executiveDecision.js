import { formatCurrency } from "../services/format.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function labelAction(item) {
  if (!item) return "—";
  return item.acao || item.title || item.message || "—";
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

export function renderExecutiveDecision(node, payload, filters, options = {}) {
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Executive Decision Engine",
    actionsHtml: `
      <button type="button" id="decisionEngineRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="decisionEngineExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const plano = payloadDetail.planoCorporativoConsolidado || {};
      const parecer = payloadDetail.parecerFinal || "";
      const decisao = payloadDetail.decisaoArquitetural || {};
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${decisao.justificativa ? `<p class="muted">${decisao.justificativa}</p>` : ""}
        ${renderTable("Top Decisões (Prioridade 1)", cockpitDetail.topDecisoes || plano.prioridade1, [
          { key: "prioridade", label: "P" },
          { key: "dominio", label: "Domínio" },
          { key: "acao", label: "Ação", render: labelAction },
          { key: "roi", label: "ROI", money: true },
          { key: "prazo", label: "Prazo" },
        ])}
        ${renderTable("Top ROI", cockpitDetail.topRoi ? [cockpitDetail.topRoi] : [], [
          { key: "acao", label: "Ação", render: labelAction },
          { key: "roi", label: "ROI", money: true },
          { key: "impacto", label: "Impacto", money: true },
        ])}
        ${renderTable("Top Riscos", cockpitDetail.topRiscos, [
          { key: "classificacaoRisco", label: "Estratégia" },
          { key: "acao", label: "Plano", render: labelAction },
          { key: "riscoNivel", label: "Severidade" },
        ])}
        ${renderTable("Plano de Ação", cockpitDetail.planoAcao, [
          { key: "prioridade", label: "P" },
          { key: "dominio", label: "Domínio" },
          { key: "acao", label: "Ação", render: labelAction },
          { key: "impacto", label: "Impacto", money: true },
          { key: "prazo", label: "Prazo" },
          { key: "responsavel", label: "Responsável", render: (r) => r.responsavel?.nome || "—" },
        ])}
      `;
    },
    refreshButtonId: "decisionEngineRefresh",
    exportButtonId: "decisionEngineExport",
    exportData: cockpit.planoAcao || [],
    exportFileName: "decision-engine.csv",
    defaultView: "executiveDecision",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
