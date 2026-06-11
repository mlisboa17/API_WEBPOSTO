import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return formatCurrency(v);
}

function label(item, nameKey = "employeeName", codeKey = "funcionarioCodigo") {
  if (!item) return "—";
  const name = item[nameKey] || item.nomeFilial || item.nome;
  const code = item[codeKey] ?? item.empresaCodigo ?? item.pdvCodigo ?? item.turno;
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

export function renderExecutiveScorecard(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Executive Scorecard…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const scores = cockpit.scores || {};
  const exec = payload.executiveAnswers || {};
  const parecer = payload.parecerFinal || "";
  const decisao = payload.decisaoArquitetural || {};

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Executive Scorecard</h2>
        <p class="muted">F04.7 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${decisao.justificativa ? `<p class="muted">${decisao.justificativa}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="scorecardRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="scorecardExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card kpi-card--highlight"><span class="kpi-label">Executive Score</span><strong>${scores.executive ?? exec["1_executiveScore"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Financial</span><strong>${scores.financial ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">People</span><strong>${scores.people ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Operations</span><strong>${scores.operations ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Growth</span><strong>${scores.growth ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Risk</span><strong>${scores.risk ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Alertas</span><strong>${exec["13_alertasExecutivos"] ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
    </div>
    ${renderTable("Top Filiais", cockpit.topFiliais, [
      { key: "nomeFilial", label: "Filial" },
      { key: "receita", label: "Receita", money: true },
    ])}
    ${renderTable("Top Operadores", cockpit.topOperadores, [
      { key: "employeeName", label: "Operador", render: (r) => label(r) },
      { key: "benchmarkScore", label: "Score" },
    ])}
    ${renderTable("Alertas Executivos", cockpit.alertas, [
      { key: "severity", label: "Severidade" },
      { key: "category", label: "Categoria" },
      { key: "message", label: "Mensagem" },
    ])}
    <section class="panel"><h3>Tendências</h3><pre>${JSON.stringify(cockpit.tendencias || {}, null, 2)}</pre></section>
  `;

  node.querySelector("#scorecardRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#scorecardExport")?.addEventListener("click", () => {
    downloadCsv("executive-scorecard.csv", cockpit.topOperadores || []);
  });
}
