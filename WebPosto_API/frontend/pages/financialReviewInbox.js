import { formatCurrency } from "../services/format.js";
import { formatMoneyInText, splitDecisionAlert } from "../services/decisionDisplay.js";

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

function renderAlertCard(item) {
  const rawTitle = item.decision_title || item.decision_category || item.request_type_label || "Solicitação";
  const { amount, context } = splitDecisionAlert(rawTitle);
  const category = formatMoneyInText(item.decision_category || "");
  const tenant = item.tenant_name || item.tenant_id || "—";

  return `
    <article class="fin-inbox-alert-card" data-request-id="${item.request_id}">
      <header class="fin-inbox-alert-card__header">
        <span class="fin-inbox-alert-card__badge">Requer atenção</span>
        <span class="fin-inbox-alert-card__tenant">${tenant}</span>
      </header>
      ${
        amount
          ? `<p class="fin-inbox-alert-card__amount">${amount}</p>
             <p class="fin-inbox-alert-card__context">${context}</p>`
          : `<p class="fin-inbox-alert-card__context fin-inbox-alert-card__context--solo">${formatMoneyInText(rawTitle)}</p>`
      }
      ${category && category !== rawTitle ? `<p class="fin-inbox-alert-card__category">${category}</p>` : ""}
      <dl class="fin-inbox-alert-card__meta">
        <div>
          <dt>Valor em revisão</dt>
          <dd>${fmtMoney(item.amount_under_review)}</dd>
        </div>
        <div>
          <dt>Lançamentos</dt>
          <dd>${item.evidence_items_count ?? 0}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>${item.financial_status_label || item.technical_status || "—"}</dd>
        </div>
      </dl>
      <p class="muted fin-inbox-alert-card__footnote">
        Solicitado pela Diretoria · ${fmtDateTime(item.requested_at)}
        ${item.review_responsible ? ` · Responsável: <strong>${item.review_responsible}</strong>` : ""}
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
          <p class="muted">Solicitações enviadas pela Diretoria — priorize o que exige validação</p>
        </div>
        <button type="button" id="finInboxRefresh" class="btn-secondary">Atualizar</button>
      </header>

      ${renderSummary(summary)}

      ${
        items.length
          ? `<div class="fin-inbox-alert-grid">${items.map(renderAlertCard).join("")}</div>`
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
