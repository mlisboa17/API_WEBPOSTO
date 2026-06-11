import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

function levelClass(level) {
  const map = {
    CRITICO: "badge-danger",
    ALTO: "badge-warn",
    ATENCAO: "badge-info",
    INFO: "badge-muted",
  };
  return map[level] || "badge-muted";
}

function renderHeatmap(cells, turns, pdvs) {
  if (!cells?.length) return "<p class=\"muted\">Sem dados de heatmap.</p>";
  const lookup = new Map(cells.map((c) => [`${c.turno}|${c.pdvCodigo}`, c]));
  const header = pdvs.map((p) => `<th>PDV ${p}</th>`).join("");
  const body = turns
    .map((turn) => {
      const tds = pdvs
        .map((pdv) => {
          const cell = lookup.get(`${turn}|${pdv}`);
          const val = cell?.impactoAbsoluto ?? 0;
          const intensity = Math.min(100, Math.round(val / 5));
          return `<td style="background:rgba(220,53,69,${intensity / 100})">${fmtMoney(val)}</td>`;
        })
        .join("");
      return `<tr><th>${turn}</th>${tds}</tr>`;
    })
    .join("");
  return `<table class="data-table heatmap"><thead><tr><th>Turno \\ PDV</th>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderList(title, items, labelKey) {
  if (!items?.length) return "";
  const rows = items
    .map(
      (item) =>
        `<tr><td>${item[labelKey]}</td><td>${item.alertas ?? item.fechamentos ?? "—"}</td><td>${fmtMoney(item.diferencaAbsoluta ?? item.diferencaAcumulada)}</td><td>${item.band || item.matrizRisco || "—"}</td></tr>`
    )
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr><th>Alvo</th><th>Qtd</th><th>Impacto</th><th>Risco</th></tr></thead><tbody>${rows}</tbody></table></section>`;
}

export function renderCashOperations(node, payload, filters, options = {}) {
  if (!node) return;
  const summary = payload?.summary || payload || {};
  const alerts = payload?.alerts || {};
  const operators = payload?.operators || {};
  const pdvs = payload?.pdvs || {};
  const turns = payload?.turns || {};
  const heatmap = payload?.heatmap || {};

  const perfMs = payload?.performanceMs?.total ?? summary?.performanceMs?.total;
  const perfNote = perfMs != null ? `<span class="muted">Render ${perfMs} ms</span>` : "";

  node.innerHTML = `
    <div class="view-header">
      <div>
        <h2>Cash Operations</h2>
        <p>Cockpit operacional de fechamento de caixa · ${filters?.dataInicial || ""} → ${filters?.dataFinal || ""}</p>
      </div>
      <div class="view-actions">
        ${perfNote}
        <button type="button" class="btn-secondary" id="cashOpsRefresh">Atualizar</button>
        <button type="button" class="btn-secondary" id="cashOpsExport">Export CSV</button>
      </div>
    </div>

    <div class="cards-grid">
      <article class="card card-impact">
        <h3>Diferença Total da Rede</h3>
        <p class="card-value">${fmtMoney(summary.diferencaTotalRede)}</p>
        <small>Impacto absoluto 7d: ${fmtMoney(summary.impactoAbsoluto7d)}</small>
      </article>
      <article class="card">
        <h3>Cash Risk Score</h3>
        <p class="card-value">${summary.cashRiskScore ?? "—"}</p>
        <small>Banda: ${summary.cashRiskBand || "—"}</small>
      </article>
      <article class="card">
        <h3>Alertas Ativos</h3>
        <p class="card-value">${summary.alertasAtivos ?? alerts.total ?? 0}</p>
        <small>Críticos: ${alerts.criticos?.length ?? 0}</small>
      </article>
      <article class="card">
        <h3>Recuperação Estimada</h3>
        <p class="card-value">${fmtMoney(summary.potencialRecuperavel30pct)}</p>
        <small>Estancamento 7d: ${fmtMoney(summary.estancamentoInicial7d)}</small>
      </article>
    </div>

    <div class="panels-grid">
      <section class="panel panel-alert">
        <h3>Alertas Operacionais</h3>
        <table class="data-table">
          <thead><tr><th>Nível</th><th>Operador</th><th>PDV</th><th>Turno</th><th>Diff</th><th>Motivo</th></tr></thead>
          <tbody>
            ${(alerts.ativos || [])
              .slice(0, 25)
              .map(
                (a) =>
                  `<tr class="${levelClass(a.nivel)}"><td>${a.nivel}</td><td>${a.funcionarioCodigo}</td><td>${a.pdvCodigo}</td><td>${a.turno || a.turnoCodigo || "—"}</td><td>${fmtMoney(a.diferenca)}</td><td>${a.motivo}</td></tr>`
              )
              .join("") || "<tr><td colspan=\"6\">Nenhum alerta ativo.</td></tr>"}
          </tbody>
        </table>
      </section>

      ${renderList("Operadores Críticos", alerts.vermelhas?.operadores, "funcionarioCodigo")}
      ${renderList("PDVs Críticos", alerts.vermelhas?.pdvs, "pdvCodigo")}
      ${renderList("Turnos Críticos", alerts.vermelhas?.turnos, "turno")}

      <section class="panel">
        <h3>Top Operadores (Piores)</h3>
        <table class="data-table">
          <thead><tr><th>Operador</th><th>Fechamentos</th><th>Diff Acum.</th><th>Score</th></tr></thead>
          <tbody>
            ${(operators.rankingPiores || [])
              .slice(0, 10)
              .map(
                (o) =>
                  `<tr><td>${o.funcionarioCodigo}</td><td>${o.fechamentos}</td><td>${fmtMoney(o.diferencaAcumulada)}</td><td>${o.cashRiskScore ?? "—"}</td></tr>`
              )
              .join("")}
          </tbody>
        </table>
      </section>

      <section class="panel">
        <h3>Top PDVs</h3>
        <table class="data-table">
          <thead><tr><th>PDV</th><th>Fechamentos</th><th>Diff Acum.</th><th>Desvio</th></tr></thead>
          <tbody>
            ${(pdvs.ranking || [])
              .slice(0, 10)
              .map(
                (p) =>
                  `<tr><td>${p.pdvCodigo}${p.monitoramentoPrioritario ? " ★" : ""}</td><td>${p.fechamentos}</td><td>${fmtMoney(p.diferencaAcumulada)}</td><td>${fmtMoney(p.desvioPadrao)}</td></tr>`
              )
              .join("")}
          </tbody>
        </table>
      </section>

      <section class="panel panel-wide">
        <h3>Heatmap Turno × PDV</h3>
        ${renderHeatmap(heatmap.cells, heatmap.turnos, heatmap.pdvs)}
      </section>
    </div>
  `;

  node.querySelector("#cashOpsRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#cashOpsExport")?.addEventListener("click", () => {
    const rows = (operators.todos || []).map((o) => ({
      funcionarioCodigo: o.funcionarioCodigo,
      fechamentos: o.fechamentos,
      diferencaAcumulada: o.diferencaAcumulada,
      cashRiskScore: o.cashRiskScore,
    }));
    downloadCsv(rows, `cash_operations_${filters?.dataInicial}_${filters?.dataFinal}.csv`);
  });
}
