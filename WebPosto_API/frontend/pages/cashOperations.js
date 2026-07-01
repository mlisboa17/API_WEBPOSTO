import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";
import { renderExecutiveCockpitPage } from "../services/executiveCockpitAdapter.js";
import { buildFourQuestionBrief, enrichAlert } from "../services/executiveBrief.js";
import { moneyKpi } from "../services/executiveKpis.js";

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
  if (!cells?.length) return '<p class="muted">Sem dados de heatmap.</p>';
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

  const exportRows = (operators.todos || []).map((o) => ({
    funcionarioCodigo: o.funcionarioCodigo,
    fechamentos: o.fechamentos,
    diferencaAcumulada: o.diferencaAcumulada,
    cashRiskScore: o.cashRiskScore,
  }));

  const alertasAtivos = summary.alertasAtivos ?? alerts.total ?? 0;
  const criticos = alerts.criticos?.length ?? 0;

  renderExecutiveCockpitPage(node, payload, filters, {
    title: "Cash Operations",
    actionsHtml: `
      ${perfMs != null ? `<span class="muted">Render ${perfMs} ms</span>` : ""}
      <button type="button" class="btn-secondary" id="cashOpsRefresh">Atualizar</button>
      <button type="button" class="btn-secondary" id="cashOpsExport">Export CSV</button>
    `,
    kpiOverrides: [
      { label: "Diferença Rede", value: moneyKpi(summary.diferencaTotalRede), trendPct: null, status: "crit" },
      { label: "Risk Score", value: String(summary.cashRiskScore ?? "—"), trendPct: null, status: "warn" },
      {
        label: "Alertas",
        value: String(alertasAtivos),
        trendPct: null,
        status: Number(alertasAtivos) > 0 ? "crit" : "ok",
      },
      { label: "Recuperável", value: moneyKpi(summary.potencialRecuperavel30pct), trendPct: null, status: "ok" },
    ],
    brief: buildFourQuestionBrief({
      what: `Diferença total da rede ${moneyKpi(summary.diferencaTotalRede)} · score ${summary.cashRiskScore ?? "—"}.`,
      why:
        criticos > 0
          ? `${criticos} alerta(s) crítico(s) ativo(s).`
          : `Impacto 7d: ${moneyKpi(summary.impactoAbsoluto7d)}.`,
      where: (alerts.vermelhas?.pdvs || [])[0]?.pdvCodigo
        ? `PDV ${(alerts.vermelhas.pdvs[0]).pdvCodigo}`
        : "Rede consolidada",
      actionNow:
        criticos > 0
          ? "Tratar alertas críticos de fechamento hoje."
          : "Monitorar operadores e PDVs no heatmap.",
    }),
    alerts: (alerts.ativos || []).slice(0, 3).map((a) =>
      enrichAlert(
        {
          severity: a.nivel === "CRITICO" ? "ALTO" : "MÉDIO",
          title: `Op. ${a.funcionarioCodigo} · PDV ${a.pdvCodigo}`,
          detail: fmtMoney(a.diferenca),
          view: "cashOperations",
          origin: "Caixa",
        },
        { why: a.motivo || "Diferença de fechamento", where: `Turno ${a.turno || a.turnoCodigo || "—"}`, actionNow: "Auditar fechamento" }
      )
    ),
    detailBuilder: (_cockpit, payloadDetail) => {
      const summaryDetail = payloadDetail?.summary || payloadDetail || {};
      const alertsDetail = payloadDetail?.alerts || {};
      const operatorsDetail = payloadDetail?.operators || {};
      const pdvsDetail = payloadDetail?.pdvs || {};
      const heatmapDetail = payloadDetail?.heatmap || {};
      return `
        <div class="cards-grid">
          <article class="card card-impact">
            <h3>Diferença Total da Rede</h3>
            <p class="card-value">${fmtMoney(summaryDetail.diferencaTotalRede)}</p>
            <small>Impacto absoluto 7d: ${fmtMoney(summaryDetail.impactoAbsoluto7d)}</small>
          </article>
          <article class="card">
            <h3>Cash Risk Score</h3>
            <p class="card-value">${summaryDetail.cashRiskScore ?? "—"}</p>
            <small>Banda: ${summaryDetail.cashRiskBand || "—"}</small>
          </article>
          <article class="card">
            <h3>Alertas Ativos</h3>
            <p class="card-value">${summaryDetail.alertasAtivos ?? alertsDetail.total ?? 0}</p>
            <small>Críticos: ${alertsDetail.criticos?.length ?? 0}</small>
          </article>
          <article class="card">
            <h3>Recuperação Estimada</h3>
            <p class="card-value">${fmtMoney(summaryDetail.potencialRecuperavel30pct)}</p>
            <small>Estancamento 7d: ${fmtMoney(summaryDetail.estancamentoInicial7d)}</small>
          </article>
        </div>
        <div class="panels-grid">
          <section class="panel panel-alert">
            <h3>Alertas Operacionais</h3>
            <table class="data-table">
              <thead><tr><th>Nível</th><th>Operador</th><th>PDV</th><th>Turno</th><th>Diff</th><th>Motivo</th></tr></thead>
              <tbody>
                ${(alertsDetail.ativos || [])
                  .slice(0, 25)
                  .map(
                    (a) =>
                      `<tr class="${levelClass(a.nivel)}"><td>${a.nivel}</td><td>${a.funcionarioCodigo}</td><td>${a.pdvCodigo}</td><td>${a.turno || a.turnoCodigo || "—"}</td><td>${fmtMoney(a.diferenca)}</td><td>${a.motivo}</td></tr>`
                  )
                  .join("") || '<tr><td colspan="6">Nenhum alerta ativo.</td></tr>'}
              </tbody>
            </table>
          </section>
          ${renderList("Operadores Críticos", alertsDetail.vermelhas?.operadores, "funcionarioCodigo")}
          ${renderList("PDVs Críticos", alertsDetail.vermelhas?.pdvs, "pdvCodigo")}
          ${renderList("Turnos Críticos", alertsDetail.vermelhas?.turnos, "turno")}
          <section class="panel">
            <h3>Top Operadores (Piores)</h3>
            <table class="data-table">
              <thead><tr><th>Operador</th><th>Fechamentos</th><th>Diff Acum.</th><th>Score</th></tr></thead>
              <tbody>
                ${(operatorsDetail.rankingPiores || [])
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
                ${(pdvsDetail.ranking || [])
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
            ${renderHeatmap(heatmapDetail.cells, heatmapDetail.turnos, heatmapDetail.pdvs)}
          </section>
        </div>`;
    },
    refreshButtonId: "cashOpsRefresh",
    exportButtonId: "cashOpsExport",
    exportData: exportRows,
    exportFileName: `cash_operations_${filters?.dataInicial}_${filters?.dataFinal}.csv`,
    defaultView: "cashOperations",
    onRefresh: options.onRefresh,
    onNavigate: options.onNavigate,
  });
}
