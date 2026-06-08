import { formatCurrency } from "../services/format.js";
import { downloadCsv, openPdfPreview } from "../services/export.js";

function fmtMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(value);
}

const EXPORT_COLUMNS = [
  { key: "periodo", label: "Período" },
  { key: "entradasPrevistas", label: "Entradas", type: "currency", formatter: fmtMoney },
  { key: "saidasPrevistas", label: "Saídas", type: "currency", formatter: fmtMoney },
  { key: "saldoProjetado", label: "Saldo Projetado", type: "currency", formatter: fmtMoney },
  { key: "saldoAcumulado", label: "Saldo Acumulado", type: "currency", formatter: fmtMoney },
];

export function buildCashFlowExportRows(data) {
  const daily = data?.daily || [];
  return daily.map((row) => ({ ...row }));
}

function renderSparkline(rows) {
  if (!rows?.length) return '<p class="small">Sem série temporal.</p>';
  const max = Math.max(...rows.map((r) => Math.abs(parseFloat(String(r.saldoAcumulado).replace(",", ".")) || 0)), 1);
  const bars = rows
    .map((r) => {
      const h = Math.round((Math.abs(parseFloat(String(r.saldoAcumulado).replace(",", ".")) || 0) / max) * 48);
      return `<span class="cf-bar" title="${r.periodo}: ${fmtMoney(r.saldoAcumulado)}" style="height:${Math.max(h, 2)}px"></span>`;
    })
    .join("");
  return `<div class="cf-sparkline" aria-hidden="true">${bars}</div>`;
}

function renderTable(rows, columns) {
  if (!rows?.length) return '<p class="small">Sem dados.</p>';
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${columns.map((c) => `<td>${c.formatter ? c.formatter(row[c.key]) : row[c.key]}</td>`).join("")}</tr>`
    )
    .join("");
  return `<table class="table-compact cf-table-export"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

export function renderCashFlow(container, data, filters, options = {}) {
  const flow = data || {};
  const cards = flow.cards || {};
  const fromSnapshot = flow.fromSnapshot ? "Snapshot" : "Live";
  const lastUpdated = flow.lastUpdated || "—";

  container.innerHTML = `
    <div class="cash-flow" data-testid="cash-flow-root">
      <div class="fc-header">
        <div>
          <h2>Fluxo de Caixa Corporativo</h2>
          <p class="small">Fatos WebPosto — TITULO_PAGAR · TITULO_RECEBER · MOVIMENTO_CONTA · CAIXA_APRESENTADO. ${fromSnapshot} · ${lastUpdated}</p>
        </div>
        <div class="fc-actions">
          <button type="button" id="cfExportCsv" data-testid="cf-export-csv">Exportar CSV</button>
          <button type="button" id="cfExportPdf" data-testid="cf-export-pdf">Exportar PDF</button>
        </div>
      </div>
      <div class="fc-cards">
        <article class="fc-card"><h3>Entradas Previstas</h3><p class="fc-val">${fmtMoney(cards.entradasPrevistas)}</p></article>
        <article class="fc-card"><h3>Saídas Previstas</h3><p class="fc-val">${fmtMoney(cards.saidasPrevistas)}</p></article>
        <article class="fc-card"><h3>Saldo Projetado</h3><p class="fc-val">${fmtMoney(cards.saldoProjetado)}</p></article>
        <article class="fc-card"><h3>Saldo Acumulado</h3><p class="fc-val">${fmtMoney(cards.saldoAcumulado)}</p></article>
      </div>
      <section class="panel"><h3>Linha temporal diária</h3>${renderSparkline(flow.daily)}${renderTable(flow.daily, EXPORT_COLUMNS)}</section>
      <div class="fc-grid">
        <section class="panel" data-testid="cf-weekly"><h3>Fluxo semanal</h3>${renderTable(flow.weekly, EXPORT_COLUMNS)}</section>
        <section class="panel" data-testid="cf-monthly"><h3>Fluxo mensal</h3>${renderTable(flow.monthly, EXPORT_COLUMNS)}</section>
        <section class="panel"><h3>Recebimentos futuros</h3>${renderFutureTable(flow.receivablesFuture)}</section>
        <section class="panel"><h3>Pagamentos futuros</h3>${renderFutureTable(flow.payablesFuture)}</section>
        <section class="panel"><h3>Eventos vencidos</h3>${renderFutureTable(flow.overdueEvents)}</section>
        <section class="panel"><h3>Tesouraria</h3>${renderTreasury(flow.treasury)}</section>
      </div>
    </div>
  `;

  const exportRows = buildCashFlowExportRows(flow);
  container.querySelector("#cfExportCsv")?.addEventListener("click", () => {
    downloadCsv(`fluxo_caixa_${filters.dataInicial}_${filters.dataFinal}`, EXPORT_COLUMNS, exportRows);
  });
  container.querySelector("#cfExportPdf")?.addEventListener("click", () => {
    openPdfPreview(`Fluxo de Caixa ${filters.dataInicial} — ${filters.dataFinal}`, EXPORT_COLUMNS, exportRows, {
      subtitle: "LOGOS SPACE — projeção rastreável, sem estimativas artificiais",
      description: "LOGOS SPACE — projeção rastreável, sem estimativas artificiais",
    });
  });
}

function renderFutureTable(items) {
  if (!items?.length) return '<p class="small">Sem dados.</p>';
  const rows = items
    .slice(0, 100)
    .map(
      (it) =>
        `<tr><td>${it.vencimento || ""}</td><td>${it.descricao || ""}</td><td>${it.aging || ""}</td><td>${fmtMoney(it.valor)}</td></tr>`
    )
    .join("");
  return `<table class="table-compact cf-table-export"><thead><tr><th>Vencimento</th><th>Descrição</th><th>Aging</th><th>Valor</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderTreasury(t) {
  if (!t) return '<p class="small">Sem dados.</p>';
  return `<ul class="fc-list">
    <li>Créditos: ${t.creditos?.count ?? 0} · ${fmtMoney(t.creditos?.valor)}</li>
    <li>Débitos: ${t.debitos?.count ?? 0} · ${fmtMoney(t.debitos?.valor)}</li>
    <li>Tarifas: ${t.tarifas?.count ?? 0} · ${fmtMoney(t.tarifas?.valor)}</li>
    <li>Transferências: ${t.transferencias?.count ?? 0} · ${fmtMoney(t.transferencias?.valor)}</li>
  </ul>`;
}
