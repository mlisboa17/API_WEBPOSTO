import { formatCurrency } from "../services/format.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";

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
  const cockpit = payload?.cockpit || {};

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Benchmark Intelligence",
    actionsHtml: `
      <button type="button" id="benchmarkRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="benchmarkExport" class="btn-secondary">Exportar CSV</button>
    `,
    detailBuilder: (cockpitDetail, payloadDetail) => {
      const parecer = payloadDetail.parecerFinal || "";
      return `
        ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
        ${renderTable("Ranking Filiais", cockpitDetail.rankingFiliais, [
          { key: "nomeFilial", label: "Filial" },
          { key: "receita", label: "Receita", money: true },
          { key: "roi", label: "ROI %" },
        ])}
        ${renderTable("Top Operadores", cockpitDetail.rankingOperadores, [
          { key: "employeeName", label: "Operador", render: (r) => label(r) },
          { key: "benchmarkScore", label: "Score" },
          { key: "resultadoLiquido", label: "Lucro", money: true },
        ])}
        ${renderTable("Ranking PDVs", cockpitDetail.rankingPdvs, [
          { key: "pdvCodigo", label: "PDV" },
          { key: "resultadoLiquido", label: "Resultado", money: true },
          { key: "roi", label: "ROI" },
        ])}
        ${renderTable("Gaps", cockpitDetail.gaps, [
          { key: "tipo", label: "Tipo" },
          { key: "gap", label: "Gap" },
        ])}
        ${renderTable("Best Practices", cockpitDetail.bestPractices, [
          { key: "padrao", label: "Padrão" },
          { key: "acao", label: "Ação" },
        ])}
      `;
    },
    refreshButtonId: "benchmarkRefresh",
    exportButtonId: "benchmarkExport",
    exportData: cockpit.rankingOperadores || [],
    exportFileName: "benchmark-intelligence.csv",
    defaultView: "benchmark",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
