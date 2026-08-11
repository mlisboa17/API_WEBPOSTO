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

function _amt(b, key, legacy) {
  const v = b?.[key];
  if (v !== undefined && v !== null) return v;
  return b?.[legacy];
}

function renderExposureBlock(exposure) {
  if (!exposure || !exposure.has_data) {
    return `<section class="panel">
      <h3>Divergência de Fechamento (CASH-01)</h3>
      <p class="muted">Sem dados de fechamento no período.</p>
      <p class="muted">Escopo: <code>CASH_CLOSING</code> — Apresentado × Apurado do WebPosto.</p>
    </section>`;
  }
  const presented = _amt(exposure, "presented_amount", "identified_amount");
  const calculated = _amt(exposure, "calculated_amount", "expected_amount");
  const difference = _amt(exposure, "difference_amount", "exposure_amount");
  const closing = exposure.closing_status || "UNKNOWN";
  const auditState = exposure.audit_state || "NOT_READY";
  const auditLabel =
    auditState === "FINAL"
      ? "Consolidado (final)"
      : auditState === "PROVISIONAL"
        ? "Fechado — aguardando consolidação (valor provisório)"
        : "Não pronto para auditoria de fechamento";
  const rows = (exposure.breakdown || [])
    .filter((b) => b.status === "OK" || b.status === "OPEN")
    .map((b) => {
      const p = _amt(b, "presented_amount", "identified_amount");
      const c = _amt(b, "calculated_amount", "expected_amount");
      const d = _amt(b, "difference_amount", "exposure_amount");
      return `
      <tr>
        <td>${b.payment_method}${b.status === "OPEN" ? " <span class='text-warn'>(aberto)</span>" : ""}</td>
        <td>${fmt(p)}</td>
        <td>${fmt(c)}</td>
        <td class="${Math.abs(d || 0) > 0.009 ? "text-crit" : ""}">${fmt(d)}</td>
        <td>${b.sangria_amount != null ? fmt(b.sangria_amount) : "—"}</td>
      </tr>`;
    })
    .join("");
  return `<section class="panel">
    <h3>Divergência de Fechamento (CASH-01)</h3>
    <p class="muted">${exposure.disclaimer || "Apresentado × Apurado — não é perda confirmada."}</p>
    <p><strong>Escopo:</strong> <code>${exposure.data_scope || "CASH_CLOSING"}</code>
       · <strong>Fechamento:</strong> <code>${closing}</code>
       · <strong>Consolidado:</strong> <code>${exposure.is_consolidated || "unknown"}</code>
       · <strong>Finalidade:</strong> <code>${auditState}</code> — ${auditLabel}
       ${exposure.open_caixa_count ? ` · caixas abertos: ${exposure.open_caixa_count}` : ""}</p>
    <dl class="recon-dl">
      <div><dt>Apresentado</dt><dd>${fmt(presented)}</dd></div>
      <div><dt>Apurado</dt><dd>${fmt(calculated)}</dd></div>
      <div><dt>Diferença</dt><dd class="${Math.abs(difference || 0) > 0.009 ? "text-crit" : ""}">${fmt(difference)}</dd></div>
    </dl>
    <table class="data-table"><thead><tr>
      <th>Meio</th><th>Apresentado</th><th>Apurado</th><th>Diferença</th><th>Sangria</th>
    </tr></thead><tbody>${rows || "<tr><td colspan='5' class='muted'>Sem breakdown</td></tr>"}</tbody></table>
  </section>`;
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
  const exposure = data.cashExposure || options.cashExposure || null;
  const pre = summary.preCheck || {};
  const progress = `${summary.naturezasConferidas || 0} de ${summary.naturezasTotal || 0} naturezas conferidas`;
  const subtitle = companySubtitle(filters, options.companies || []);

  const presentedKpi = exposure?.presented_amount ?? exposure?.identified_amount ?? summary.valorApresentado;
  const calculatedKpi = exposure?.calculated_amount ?? exposure?.expected_amount ?? summary.valorApurado;
  const differenceKpi = exposure?.difference_amount ?? exposure?.exposure_amount ?? summary.valorDivergente;
  const kpis = [
    { label: "Apresentado", value: fmt(presentedKpi), status: "ok" },
    { label: "Apurado", value: fmt(calculatedKpi), status: "ok" },
    {
      label: "Diferença de Fechamento",
      value: fmt(differenceKpi),
      status: Math.abs(differenceKpi || 0) > 0.009 ? "crit" : "ok",
    },
    {
      label: "Finalidade",
      value: exposure?.audit_state || "NOT_READY",
      status: exposure?.audit_state === "FINAL" ? "ok" : "warn",
    },
  ];

  const detailHtml = `
    ${renderExposureBlock(exposure)}
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
