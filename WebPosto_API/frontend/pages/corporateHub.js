import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

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
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Corporate Intelligence Hub…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const parecer = payload.parecerFinal || "";
  const decisao = payload.decisaoArquitetural || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Corporate Intelligence Hub</h2>
        <p class="muted">F05.0 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${decisao.justificativa ? `<p class="muted">${decisao.justificativa}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="corporateHubRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="corporateHubExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Corporate Score</span><strong>${cockpit.corporateScore ?? exec["1_corporateScore"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Executive</span><strong>${cockpit.executiveScore ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Financial</span><strong>${cockpit.financialScore ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">People</span><strong>${cockpit.peopleScore ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Operations</span><strong>${cockpit.operationsScore ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Recuperável</span><strong>${fmtMoney(exec["14_podeRecuperar"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Hub Confiável</span><strong>${exec["18_hubConfiavel"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Top Oportunidades", cockpit.topOportunidades, [
      { key: "prioridade", label: "Prioridade" },
      { key: "title", label: "Oportunidade" },
      { key: "impactoEstimado", label: "Impacto", money: true },
    ])}
    ${renderTable("Top Riscos", cockpit.topRiscos, [
      { key: "severity", label: "Severidade" },
      { key: "riskType", label: "Tipo" },
      { key: "message", label: "Mensagem" },
    ])}
    ${renderTable("Top Operadores", cockpit.topOperadores, [
      { key: "employeeName", label: "Operador", render: (r) => label(r) },
      { key: "benchmarkScore", label: "Score" },
    ])}
    ${renderTable("Alertas Corporativos", cockpit.alertasCorporativos, [
      { key: "severity", label: "Severidade" },
      { key: "category", label: "Categoria" },
      { key: "message", label: "Mensagem" },
    ])}
  `;

  node.querySelector("#corporateHubRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#corporateHubExport")?.addEventListener("click", () => {
    downloadCsv("corporate-hub.csv", cockpit.topOportunidades || []);
  });
}
