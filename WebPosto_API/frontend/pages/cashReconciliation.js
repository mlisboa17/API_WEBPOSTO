import { formatCurrency } from "../services/format.js";
import { renderExecutiveEmptyState, bindExecutiveNav, companySubtitle } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";

function fmt(v) {
  if (v == null || v === "") return "—";
  return formatCurrency(v);
}

function statusBadge(status) {
  const map = {
    AUTO_MATCHED: "ok",
    CONFIRMED: "ok",
    JUSTIFIED: "warn",
    NEEDS_REVIEW: "warn",
    DIVERGENT: "crit",
    NOT_REVIEWED: "warn",
    IN_REVIEW: "warn",
  };
  const tone = map[status] || "warn";
  return `<span class="exec-tag exec-tag--${tone}">${status || "PENDENTE"}</span>`;
}

function renderNatureCards(cards = []) {
  if (!cards.length) return `<p class="muted">Nenhuma natureza com movimento no período.</p>`;
  return cards
    .map(
      (c) => `
      <article class="panel recon-nature-card">
        <header><h4>${c.label || c.paymentNature}</h4>${statusBadge(c.status)}</header>
        <dl class="recon-dl">
          <div><dt>Apurado</dt><dd>${fmt(c.valorApurado)}</dd></div>
          <div><dt>Apresentado</dt><dd>${fmt(c.valorApresentado)}</dd></div>
          ${c.sangria != null ? `<div><dt>Sangria</dt><dd>${fmt(c.sangria)}</dd></div>` : ""}
          <div><dt>Diferença</dt><dd class="${Math.abs(c.diferenca || 0) > 10 ? "text-crit" : ""}">${fmt(c.diferenca)}</dd></div>
        </dl>
        <footer class="muted">${c.reviewedCount || 0}/${c.itemsCount || 0} turnos revisados</footer>
      </article>
    `
    )
    .join("");
}

function renderExceptions(items = []) {
  if (!items.length) return `<p class="muted">Nenhuma exceção prioritária — pré-conferência limpa.</p>`;
  const rows = items
    .slice(0, 30)
    .map(
      (i) => `
      <tr>
        <td>${i.paymentNature}</td>
        <td>${i.caixaCodigo ?? "—"}</td>
        <td>${i.captureOrigin || "—"}</td>
        <td>${fmt(i.valorApresentado)}</td>
        <td>${fmt(i.valorApurado)}</td>
        <td>${fmt(i.diferenca)}</td>
        <td>${statusBadge(i.status)}</td>
      </tr>
    `
    )
    .join("");
  return `<table class="data-table"><thead><tr>
    <th>Natureza</th><th>Caixa</th><th>Origem</th><th>Apresentado</th><th>Apurado</th><th>Dif.</th><th>Status</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function renderAuditSignals(signals = []) {
  if (!signals.length) return `<p class="muted">Nenhum sinal determinístico no período.</p>`;
  return signals
    .slice(0, 12)
    .map(
      (s) => `
      <li class="exec-decision-item">
        <strong>${s.signalType}</strong> · ${s.severity}
        <p>${s.explanation}</p>
        <em>${s.entityType}: ${s.entityId}</em>
      </li>
    `
    )
    .join("");
}

export function renderCashReconciliation(node, payload, filters, options = {}) {
  if (!node) return;
  const data = payload?.data || payload;
  if (!data?.summary) {
    node.innerHTML = renderExecutiveEmptyState({
      title: "Conferência Financeira",
      message: "Não foi possível carregar a conferência para o período selecionado.",
    });
    return;
  }

  const summary = data.summary;
  const pre = summary.preCheck || {};
  const progress = `${summary.naturezasConferidas || 0} de ${summary.naturezasTotal || 0} naturezas conferidas`;
  const subtitle = companySubtitle(filters, options.companies || []);

  const kpis = [
    { label: "Valor apurado", value: fmt(summary.valorApurado), status: "ok" },
    { label: "Valor conferido", value: fmt(summary.valorConferido), status: "ok" },
    { label: "Valor divergente", value: fmt(summary.valorDivergente), status: summary.valorDivergente > 0 ? "crit" : "ok" },
    { label: "Valor pendente", value: fmt(summary.valorPendente), status: summary.valorPendente > 0 ? "warn" : "ok" },
  ];

  const detailHtml = `
    <section class="panel"><h3>Progresso</h3>
      <p class="recon-progress">${progress}</p>
      <p class="muted">Pré-conferência: ${pre.autoMatched || 0} automático · ${pre.needsReview || 0} revisão · ${pre.divergent || 0} divergente · ${fmt(pre.divergentAmount)}</p>
    </section>
    <section class="panel"><h3>Naturezas com movimento</h3><div class="recon-nature-grid">${renderNatureCards(summary.natureCards)}</div></section>
    <section class="panel"><h3>Exceções prioritárias</h3>${renderExceptions(data.exceptions)}</section>
    <section class="panel"><h3>Insights do Auditor</h3><ul class="exec-decision-list">${renderAuditSignals(summary.auditSignals)}</ul></section>
    <p><button type="button" id="reconRefresh" class="btn-secondary">Atualizar conferência</button></p>
  `;

  const body = buildExecutivePageHtml({
    title: "Conferência Financeira",
    subtitle: `${subtitle} · ${filters.dataInicial} a ${filters.dataFinal}`,
    kpis,
    detailHtml,
    detailSummary: "Conferência por natureza",
  });

  node.innerHTML = body;
  bindExecutiveNav(node);
  node.querySelector("#reconRefresh")?.addEventListener("click", () => options.onRefresh?.());
}
