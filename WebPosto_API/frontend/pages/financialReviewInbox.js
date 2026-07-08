import { formatCurrency } from "../services/format.js";

function fmtMoney(value) {
  if (value == null || value === "") return "Indisponível";
  return formatCurrency(value);
}

function fmtDateTime(value) {
  if (!value) return "Indisponível";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch {
    return String(value);
  }
}

function renderSummary(summary) {
  const s = summary || {};
  if (!s.active_count) {
    return `<p class="muted">Nenhuma conferência aguardando análise.</p>`;
  }
  return `
    <dl class="fin-inbox-summary">
      <div><dt>Aguardando análise</dt><dd>${s.awaiting_analysis_count ?? 0}</dd></div>
      <div><dt>Atribuídas</dt><dd>${s.assigned_count ?? 0}</dd></div>
      <div><dt>Valor em revisão</dt><dd>${fmtMoney(s.total_amount_under_review)}</dd></div>
    </dl>
    <p class="muted fin-inbox-note">Valor em revisão — não constitui perda confirmada.</p>`;
}

function renderInboxCard(item) {
  const title = item.decision_title || item.decision_category || item.request_type_label || "Solicitação";
  return `
    <article class="fin-inbox-card" data-request-id="${item.request_id}">
      <header>
        <span class="fin-inbox-card__tenant">${item.tenant_name || item.tenant_id || "—"}</span>
        <span class="fin-inbox-card__status">${item.financial_status_label || item.technical_status}</span>
      </header>
      <h3>${title}</h3>
      <p class="fin-inbox-card__amount">
        ${item.evidence_items_count} lançamento(s) aguardando conferência · ${fmtMoney(item.amount_under_review)}
      </p>
      <p class="muted">
        Solicitado pela Diretoria · ${fmtDateTime(item.requested_at)}
        ${item.review_responsible ? ` · Responsável: ${item.review_responsible}` : ""}
      </p>
      <button type="button" class="btn-primary fin-open-review" data-request-id="${item.request_id}">
        Abrir conferência
      </button>
    </article>`;
}

export function renderFinancialReviewInbox(node, payload, filters, options = {}) {
  if (!node) return;

  if (!payload?.data) {
    node.innerHTML = `
      <section class="panel fin-inbox">
        <h2>Conferências</h2>
        <p class="muted">Não foi possível carregar a caixa de trabalho financeira.</p>
        <button type="button" id="finInboxRefresh" class="btn-secondary">Tentar novamente</button>
      </section>`;
    node.querySelector("#finInboxRefresh")?.addEventListener("click", () => options.onRefresh?.());
    return;
  }

  const data = payload.data;
  const items = data.items || [];
  const summary = data.summary || {};

  node.innerHTML = `
    <section class="panel fin-inbox">
      <header class="dir-home__header">
        <div>
          <h2>Conferências</h2>
          <p class="muted">Solicitações enviadas pela Diretoria para análise financeira</p>
        </div>
        <button type="button" id="finInboxRefresh" class="btn-secondary">Atualizar</button>
      </header>

      ${renderSummary(summary)}

      ${
        items.length
          ? `<div class="dir-decision-grid">${items.map(renderInboxCard).join("")}</div>`
          : `<div class="dir-empty">
              <p>Nenhuma conferência aguardando análise.</p>
              <p class="muted">Quando a Diretoria solicitar uma conferência, ela aparecerá aqui.</p>
            </div>`
      }
    </section>`;

  node.querySelector("#finInboxRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelectorAll(".fin-open-review").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-request-id");
      if (id) options.onOpenReview?.(id);
    });
  });
}
