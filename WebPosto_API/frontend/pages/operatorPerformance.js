import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function bandClass(band) {
  const map = {
    Excelente: "badge-success",
    Bom: "badge-info",
    Atencao: "badge-warn",
    Critico: "badge-danger",
  };
  return map[band] || "badge-muted";
}

function renderRanking(title, items, idKey, labelPrefix = "") {
  if (!items?.length) return "";
  const rows = items
    .map(
      (item) => `
      <tr>
        <td>${labelPrefix}${item[idKey] ?? "—"}</td>
        <td>${item.performanceScore ?? "—"}</td>
        <td><span class="badge ${bandClass(item.performanceBand)}">${item.performanceBand || "—"}</span></td>
        <td>${fmtMoney(item.diferencaAcumulada ?? item.desvioAcumulado)}</td>
        <td>${item.indiceRecorrencia ?? item.incidenciaQuebraPct ?? "—"}</td>
        <td>${item.cashRiskScore ?? "—"}</td>
        <td>${fmtMoney(item.saldoLedger)}</td>
      </tr>`
    )
    .join("");
  return `
    <section class="panel">
      <h3>${title}</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Alvo</th><th>Score</th><th>Banda</th><th>Dif. Acum.</th><th>Recorrência</th><th>Risk</th><th>Saldo Ledger</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </section>`;
}

function renderHeatmap(cells, rows, cols, rowKey, colKey) {
  if (!cells?.length) return "<p class=\"muted\">Sem dados de heatmap.</p>";
  const lookup = new Map(cells.map((c) => [`${c[rowKey]}|${c[colKey]}`, c]));
  const header = cols.map((c) => `<th>${colKey} ${c}</th>`).join("");
  const body = rows
    .map((row) => {
      const tds = cols
        .map((col) => {
          const cell = lookup.get(`${row}|${col}`);
          const val = cell?.impactoAbsoluto ?? 0;
          const intensity = Math.min(100, Math.round(val / 5));
          return `<td style="background:rgba(40,167,69,${1 - intensity / 100})">${fmtMoney(val)}</td>`;
        })
        .join("");
      return `<tr><th>${rowKey} ${row}</th>${tds}</tr>`;
    })
    .join("");
  return `<table class="data-table heatmap"><thead><tr><th>\\ ${colKey}</th>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderIntelTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .map((item) => {
      const cells = columns.map((c) => `<td>${item[c.key] ?? "—"}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `
    <section class="panel">
      <h3>${title}</h3>
      <table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
    </section>`;
}

export function renderOperatorPerformance(node, payload, filters, options = {}) {
  if (!node) return;
  const summary = payload?.summary || {};
  const operators = payload?.operators || {};
  const pdvs = payload?.pdvs || {};
  const turns = payload?.turns || {};
  const heatmaps = payload?.heatmaps || {};
  const evolution = payload?.evolution || {};
  const intel = payload?.intelligence || {};
  const exec = payload?.executiveAnswers || {};

  const bestOp = summary.melhorOperador || {};
  const worstOp = summary.piorOperador || {};
  const bestPdv = summary.melhorPdv || {};
  const worstPdv = summary.piorPdv || {};
  const bestTurn = summary.melhorTurno || {};
  const worstTurn = summary.piorTurno || {};

  node.innerHTML = `
    <div class="view-header">
      <div>
        <h2>Operator Performance</h2>
        <p>F04.0 Sales Intelligence · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
        ${payload?.parecerFinal ? `<small class="muted">${payload.parecerFinal}</small>` : ""}
      </div>
      <div class="view-actions">
        <button type="button" class="btn-secondary" id="perfRefresh">Atualizar</button>
        <button type="button" class="btn-secondary" id="perfExport">Export CSV</button>
      </div>
    </div>

    <div class="cards-grid">
      <article class="card card-impact">
        <h3>Melhor Operador</h3>
        <p class="card-value">${bestOp.funcionarioCodigo ?? "—"}</p>
        <small>Score ${bestOp.performanceScore ?? "—"} · ${bestOp.performanceBand ?? ""}</small>
      </article>
      <article class="card">
        <h3>Pior Operador</h3>
        <p class="card-value">${worstOp.funcionarioCodigo ?? "—"}</p>
        <small>Score ${worstOp.performanceScore ?? "—"} · ${worstOp.performanceBand ?? ""}</small>
      </article>
      <article class="card">
        <h3>Melhor PDV</h3>
        <p class="card-value">${bestPdv.pdvCodigo ?? "—"}</p>
        <small>Score ${bestPdv.performanceScore ?? "—"}</small>
      </article>
      <article class="card">
        <h3>Pior PDV</h3>
        <p class="card-value">${worstPdv.pdvCodigo ?? "—"}</p>
        <small>Score ${worstPdv.performanceScore ?? "—"}</small>
      </article>
      <article class="card">
        <h3>Melhor Turno</h3>
        <p class="card-value">${bestTurn.turno ?? bestTurn.turnoCodigo ?? "—"}</p>
        <small>Score ${bestTurn.performanceScore ?? "—"}</small>
      </article>
      <article class="card">
        <h3>Pior Turno</h3>
        <p class="card-value">${worstTurn.turno ?? worstTurn.turnoCodigo ?? "—"}</p>
        <small>Score ${worstTurn.performanceScore ?? "—"}</small>
      </article>
      <article class="card">
        <h3>Score Médio Rede</h3>
        <p class="card-value">${summary.operatorPerformanceScoreMedio ?? "—"}</p>
        <small>Excelente: ${summary.excelentes ?? 0} · Crítico: ${summary.criticos ?? 0}</small>
      </article>
      <article class="card card-impact">
        <h3>Top Vendas F04</h3>
        <p class="card-value">${exec?.["2_quemMaisVende"]?.employeeName || exec?.["2_quemMaisVende"]?.funcionarioCodigo || "—"}</p>
        <small>${fmtMoney(exec?.["2_quemMaisVende"]?.totalVendas)}</small>
      </article>
      <article class="card">
        <h3>Em Risco</h3>
        <p class="card-value">${exec?.["17_operadoresEmRisco"] ?? "—"}</p>
        <small>Produtividade ELITE · ${exec?.["15_operadorElite"]?.employeeName || "—"}</small>
      </article>
    </div>

    <div class="panels-grid">
      ${renderIntelTable("Top Operadores (Produtividade)", intel.topOperadores || [], [
        { key: "employeeName", label: "Operador" },
        { key: "productivityScore", label: "Score" },
        { key: "productivityBand", label: "Banda" },
        { key: "totalVendas", label: "Vendas" },
      ])}
      ${renderIntelTable("Operadores Críticos (Risco)", intel.operadoresCriticos || [], [
        { key: "employeeName", label: "Operador" },
        { key: "operatorRiskScore", label: "Risco" },
        { key: "riskBand", label: "Banda" },
      ])}
      ${renderIntelTable("Descontos por Operador", intel.descontos || [], [
        { key: "employeeName", label: "Operador" },
        { key: "totalDesconto", label: "Total" },
      ])}
      ${renderIntelTable("Accountability (Saldo)", intel.accountability || [], [
        { key: "employeeName", label: "Operador" },
        { key: "saldoOperacional", label: "Saldo" },
        { key: "diferencaAcumulada", label: "Dif. Caixa" },
      ])}
    </div>

    <div class="panels-grid">
      ${renderRanking("Top 20 Operadores", operators.ranking || operators.topMelhores, "funcionarioCodigo", "Op. ")}
      ${renderRanking("Top 20 PDVs", pdvs.ranking || pdvs.topMelhores, "pdvCodigo", "PDV ")}
      ${renderRanking("Ranking Turnos", turns.ranking || turns.topMelhores, "turnoCodigo", "Turno ")}
    </div>

    <div class="panels-grid">
      <section class="panel">
        <h3>Heatmap Operador × PDV</h3>
        ${renderHeatmap(
          heatmaps.operadorPdv?.cells,
          heatmaps.operadorPdv?.rows,
          heatmaps.operadorPdv?.cols,
          "funcionarioCodigo",
          "pdvCodigo"
        )}
      </section>
      <section class="panel">
        <h3>Heatmap Operador × Turno</h3>
        ${renderHeatmap(
          heatmaps.operadorTurno?.cells,
          heatmaps.operadorTurno?.rows,
          heatmaps.operadorTurno?.cols,
          "funcionarioCodigo",
          "turno"
        )}
      </section>
    </div>

    <div class="panels-grid">
      ${renderRanking("Melhorando (90d vs 7d)", evolution.melhorando, "funcionarioCodigo", "Op. ")}
      ${renderRanking("Piorando (90d vs 7d)", evolution.piorando, "funcionarioCodigo", "Op. ")}
    </div>
  `;

  node.querySelector("#perfRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#perfExport")?.addEventListener("click", () => {
    const rows = (operators.todos || operators.ranking || []).map((r) => ({
      funcionarioCodigo: r.funcionarioCodigo,
      performanceScore: r.performanceScore,
      performanceBand: r.performanceBand,
      diferencaAcumulada: r.diferencaAcumulada,
      saldoLedger: r.saldoLedger,
    }));
    downloadCsv(`operator_performance_${filters?.dataFinal || "export"}`, rows);
  });
}
