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

export function renderBenchmark(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Carregando Benchmark Intelligence…</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const qa = payload.qa || {};
  const parecer = payload.parecerFinal || "";

  node.innerHTML = `
    <header class="view-header">
      <div>
        <h2>Benchmark Intelligence</h2>
        <p class="muted">F04.6 · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" id="benchmarkRefresh" class="btn-secondary">Atualizar</button>
        <button type="button" id="benchmarkExport" class="btn-secondary">Exportar CSV</button>
      </div>
    </header>
    <div class="kpi-grid">
      <article class="kpi-card"><span class="kpi-label">Melhor Filial</span><strong>${label(exec["1_melhorFilial"], "nomeFilial", "empresaCodigo")}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Melhor Operador</span><strong>${label(exec["3_melhorOperador"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Melhor PDV</span><strong>${label(exec["5_melhorPdv"], "pdvCodigo", "pdvCodigo")}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Potencial Capturável</span><strong>${fmtMoney(exec["15_potencialCapturavel"])}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Paridade Δ</span><strong>${exec.paridadeDelta ?? "—"}</strong></article>
      <article class="kpi-card"><span class="kpi-label">Benchmark Confiável</span><strong>${exec["18_benchmarkConfiavel"] ? "Sim" : "Não"}</strong></article>
    </div>
    ${renderTable("Ranking Filiais", cockpit.rankingFiliais, [
      { key: "nomeFilial", label: "Filial" },
      { key: "receita", label: "Receita", money: true },
      { key: "roi", label: "ROI %" },
    ])}
    ${renderTable("Top Operadores", cockpit.rankingOperadores, [
      { key: "employeeName", label: "Operador", render: (r) => label(r) },
      { key: "benchmarkScore", label: "Score" },
      { key: "resultadoLiquido", label: "Lucro", money: true },
    ])}
    ${renderTable("Ranking PDVs", cockpit.rankingPdvs, [
      { key: "pdvCodigo", label: "PDV" },
      { key: "resultadoLiquido", label: "Resultado", money: true },
      { key: "roi", label: "ROI" },
    ])}
    ${renderTable("Gaps", cockpit.gaps, [
      { key: "tipo", label: "Tipo" },
      { key: "gap", label: "Gap" },
    ])}
    ${renderTable("Best Practices", cockpit.bestPractices, [
      { key: "padrao", label: "Padrão" },
      { key: "acao", label: "Ação" },
    ])}
  `;

  node.querySelector("#benchmarkRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#benchmarkExport")?.addEventListener("click", () => {
    downloadCsv("benchmark-intelligence.csv", cockpit.rankingOperadores || []);
  });
}
